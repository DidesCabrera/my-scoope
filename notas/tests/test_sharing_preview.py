from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from notas.domain.models import InboxItem, ShareClaim, ShareResource


class SharingPreviewTests(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user("preview-sender")
        self.recipient = User.objects.create_user("preview-recipient")
        self.resource = ShareResource.objects.create(
            sender=self.sender,
            subject_type=ShareResource.SubjectType.DAILY_PLAN,
            snapshot_schema_version="sharing.snapshot.v1",
            snapshot={
                "schema_version": "sharing.snapshot.v1",
                "subject": {"type": "daily_plan", "title": "Plan visible"},
                "summary": {"meal_count": 0, "food_count": 0},
                "nutrition": {"calories": 0, "protein_grams": 0, "carbs_grams": 0, "fat_grams": 0},
                "meals": [],
            },
        )
        self.preview_url = reverse("share_preview", kwargs={"public_id": self.resource.public_id})
        self.claim_url = reverse("share_claim", kwargs={"public_id": self.resource.public_id})

    def test_public_get_renders_snapshot_without_claiming(self):
        response = self.client.get(self.preview_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Plan visible")
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertEqual(ShareClaim.objects.count(), 0)
        self.assertEqual(InboxItem.objects.count(), 0)

    def test_anonymous_post_preserves_intent_but_login_return_does_not_claim(self):
        response = self.client.post(self.claim_url)

        expected_next = self.preview_url + "?claim=continue"
        self.assertRedirects(
            response,
            reverse("account_login") + "?next=" + expected_next.replace("?", "%3F").replace("=", "%3D"),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.session["pending_share_claim_public_id"], str(self.resource.public_id))
        self.client.force_login(self.recipient)
        returned = self.client.get(expected_next)
        self.assertContains(returned, "Confirmar y agregar")
        self.assertEqual(ShareClaim.objects.count(), 0)

    def test_authenticated_claim_is_explicit_and_idempotent(self):
        self.client.force_login(self.recipient)

        first = self.client.post(self.claim_url)
        second = self.client.post(self.claim_url)

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(ShareClaim.objects.filter(user=self.recipient).count(), 1)
        self.assertEqual(InboxItem.objects.filter(owner=self.recipient).count(), 1)

    def test_revoked_resource_is_not_disclosed_or_claimed(self):
        self.resource.status = ShareResource.Status.REVOKED
        self.resource.save(update_fields=["status"])
        self.client.force_login(self.recipient)

        self.assertEqual(self.client.get(self.preview_url).status_code, 404)
        self.assertEqual(self.client.post(self.claim_url).status_code, 404)
        self.assertEqual(ShareClaim.objects.count(), 0)

    def test_claim_url_rejects_get(self):
        self.assertEqual(self.client.get(self.claim_url).status_code, 405)
