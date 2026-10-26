from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone
from allauth.account.models import EmailAddress

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.sharing.services import claim_share_resource
from notas.domain.models import (
    InboxItem,
    NutritionProposal,
    ProductAnnouncement,
    ProductAnnouncementRead,
    ShareClaim,
    ShareInvitation,
    ShareResource,
)


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class NotificationCenterTests(AuthenticatedMobileAPITestCase):
    def setUp(self):
        super().setUp()
        self.other = User.objects.create_user("other-notification-user", email="other@example.com")
        self.proposal = NutritionProposal.objects.create(
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Nueva propuesta",
            summary="Revisa esta propuesta.",
        )
        NutritionProposal.objects.create(
            created_by=self.other,
            source=NutritionProposal.SOURCE_AI,
            title="Propuesta ajena",
        )
        self.resource = ShareResource.objects.create(
            sender=self.other,
            subject_type=ShareResource.SubjectType.MEAL,
            snapshot={"subject": {"title": "Comida compartida"}},
            snapshot_schema_version="test-v1",
        )
        claim = ShareClaim.objects.create(resource=self.resource, user=self.user, source=ShareClaim.Source.LINK)
        self.share = InboxItem.objects.create(owner=self.user, resource=self.resource, claim=claim)
        self.announcement = ProductAnnouncement.objects.create(
            title="Novedad de My Scoope", body="Ya puedes ver las novedades aquí.", is_active=True,
        )
        ProductAnnouncement.objects.create(
            title="Novedad futura", body="Todavía no publicada.", is_active=True,
            published_at=timezone.now() + timedelta(days=1),
        )
        self.web_client = Client()
        self.web_client.force_login(self.user)

    def test_feed_is_private_and_uses_existing_read_state(self):
        response = self.client.get("/api/v1/notifications")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["unread_count"], 3)
        self.assertEqual({item["kind"] for item in data["items"]}, {"proposal", "share", "announcement"})
        self.assertNotContains(response, "Propuesta ajena")
        self.assertNotContains(response, "Novedad futura")
        self.assertEqual(Client().get("/api/v1/notifications").status_code, 401)

    def test_mobile_read_updates_web_badge_and_existing_records(self):
        self.assertEqual(self.client.post(f"/api/v1/notifications/proposal/{self.proposal.id}/read").status_code, 200)
        self.assertEqual(self.client.post(f"/api/v1/notifications/share/{self.share.id}/read").status_code, 200)
        self.assertEqual(self.client.post(f"/api/v1/notifications/announcement/{self.announcement.id}/read").status_code, 200)
        self.proposal.refresh_from_db()
        self.share.refresh_from_db()
        self.assertTrue(self.proposal.is_read)
        self.assertIsNotNone(self.share.read_at)
        self.assertTrue(ProductAnnouncementRead.objects.filter(user=self.user, announcement=self.announcement).exists())
        self.assertEqual(self.client.get("/api/v1/notifications").json()["data"]["unread_count"], 0)
        web = self.web_client.get(reverse("notifications_list"))
        self.assertEqual(web.context["notification_unread_count"], 0)

    def test_web_read_redirects_and_rejects_another_users_item(self):
        response = self.web_client.get(reverse("notifications_list"))
        self.assertContains(response, "sidebar-notifications-unread")
        self.assertContains(response, "Nueva propuesta")
        read = self.web_client.post(reverse("notification_read", args=["share", self.share.id]))
        self.assertRedirects(read, reverse("inbox_detail", args=["share", self.share.id]), fetch_redirect_response=False)
        self.share.refresh_from_db()
        self.assertIsNotNone(self.share.read_at)
        alien = NutritionProposal.objects.get(title="Propuesta ajena")
        self.assertEqual(self.client.post(f"/api/v1/notifications/proposal/{alien.id}/read").status_code, 404)
        self.assertEqual(self.web_client.post(reverse("notification_read", args=["proposal", alien.id])).status_code, 404)

    def test_announcements_are_opt_in_to_publication_and_read_per_user(self):
        self.web_client.post(reverse("notification_read", args=["announcement", self.announcement.id]))
        self.assertEqual(self.client.get("/api/v1/notifications").json()["data"]["unread_count"], 2)
        self.assertFalse(ProductAnnouncementRead.objects.filter(user=self.other).exists())
        self.announcement.is_active = False
        self.announcement.save(update_fields=["is_active"])
        self.assertEqual(self.client.post(f"/api/v1/notifications/announcement/{self.announcement.id}/read").status_code, 404)

    def test_verified_email_invitation_appears_before_claim_without_duplicate_unread(self):
        resource = ShareResource.objects.create(
            sender=self.other, subject_type=ShareResource.SubjectType.FOOD,
            snapshot={"subject": {"title": "Alimento invitado"}}, snapshot_schema_version="test-v1",
        )
        invitation = ShareInvitation.objects.create(
            resource=resource, recipient_email=self.user.email, subject="Para tu librería",
            status=ShareInvitation.Status.DELIVERED,
        )
        self.assertEqual(self.client.get("/api/v1/notifications").json()["data"]["unread_count"], 3)
        EmailAddress.objects.create(user=self.user, email=self.user.email, verified=True, primary=True)
        feed = self.client.get("/api/v1/notifications").json()["data"]
        self.assertEqual(feed["unread_count"], 4)
        self.assertIn("invitation", {item["kind"] for item in feed["items"]})
        self.client.post(f"/api/v1/notifications/invitation/{invitation.id}/read")
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.read_at)
        _, inbox_item = claim_share_resource(resource=resource, user=self.user, source=ShareClaim.Source.EMAIL, invitation=invitation)
        self.assertIsNotNone(inbox_item.read_at)
        self.assertEqual(self.client.get("/api/v1/notifications").json()["data"]["unread_count"], 3)
