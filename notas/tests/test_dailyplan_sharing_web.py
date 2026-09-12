from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from notas.domain.models import DailyPlan, DailyPlanShare, InboxItem, ShareInvitation, ShareResource

User = get_user_model()


@override_settings(
    NUTRITION_ONBOARDING_GATE_ENABLED=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_SHARE_DELIVERY_ENABLED=True,
    EMAIL_SHARE_RECIPIENT_COOLDOWN_SECONDS=0,
)
class DailyPlanSharingWebTests(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user(
            username="web-sender",
            email="sender@example.com",
            password="strong-password",
        )
        EmailAddress.objects.create(
            user=self.sender,
            email=self.sender.email,
            verified=True,
            primary=True,
        )
        self.recipient = User.objects.create_user(
            username="web-recipient",
            email="recipient@example.com",
            password="strong-password",
        )
        self.plan = DailyPlan.objects.create(
            name="Plan web portable",
            created_by=self.sender,
            is_draft=False,
        )
        self.share_page = reverse("dailyplan_share", args=[self.plan.pk])
        self.client.force_login(self.sender)

    def test_link_action_creates_one_reusable_normalized_resource(self):
        first = self.client.post(
            self.share_page,
            {"share_action": "create_link"},
            follow=True,
        )
        second = self.client.post(
            self.share_page,
            {"share_action": "create_link"},
            follow=True,
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        resource = ShareResource.objects.get()
        self.assertContains(second, reverse("share_preview", args=[resource.public_id]))
        self.assertEqual(DailyPlanShare.objects.count(), 0)

    def test_email_uses_normalized_invitation_and_safe_preview(self):
        response = self.client.post(
            self.share_page,
            {
                "share_action": "send_email",
                "recipient_email": self.recipient.email,
                "subject": "Mira este plan",
                "message": "Lo preparé para ti.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        invitation = ShareInvitation.objects.select_related("resource").get()
        self.assertEqual(invitation.status, ShareInvitation.Status.DELIVERED)
        self.assertEqual(invitation.subject, "Mira este plan")
        self.assertEqual(DailyPlanShare.objects.count(), 0)
        invitation_url = reverse("share_invitation_preview", args=[invitation.public_id])
        self.assertIn(invitation_url, mail.outbox[0].body)

        self.client.logout()
        preview = self.client.get(invitation_url)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(InboxItem.objects.count(), 0)
        self.assertContains(
            preview,
            reverse("share_invitation_card", args=[invitation.public_id]),
        )
        self.assertNotContains(preview, f"myscoope://share/{invitation.resource.public_id}")

    def test_directed_claim_requires_matching_verified_email(self):
        resource = ShareResource.objects.create(
            sender=self.sender,
            subject_type=ShareResource.SubjectType.DAILY_PLAN,
            snapshot={
                "subject": {"type": "daily_plan", "title": "Plan dirigido"},
                "summary": {"meal_count": 0, "food_count": 0},
                "nutrition": {"calories": 0, "protein_grams": 0, "carbs_grams": 0, "fat_grams": 0},
                "meals": [],
            },
            snapshot_schema_version="sharing.snapshot.v1",
        )
        invitation = ShareInvitation.objects.create(
            resource=resource,
            recipient_email=self.recipient.email,
        )
        claim_url = reverse("share_invitation_claim", args=[invitation.public_id])
        self.client.force_login(self.recipient)
        self.assertEqual(self.client.post(claim_url).status_code, 409)

        EmailAddress.objects.create(
            user=self.recipient,
            email=self.recipient.email,
            verified=True,
            primary=True,
        )
        claimed = self.client.post(claim_url)
        self.assertEqual(claimed.status_code, 302)
        self.assertEqual(InboxItem.objects.filter(owner=self.recipient).count(), 1)

    @override_settings(RATE_LIMIT_SHARING_CREATE_USER="1/h")
    def test_web_share_creation_is_rate_limited_per_user(self):
        cache.clear()
        try:
            first = self.client.post(self.share_page, {"share_action": "create_link"})
            second = self.client.post(self.share_page, {"share_action": "create_link"})
            self.assertEqual(first.status_code, 302)
            self.assertEqual(second.status_code, 403)
        finally:
            cache.clear()
