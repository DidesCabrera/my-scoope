from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from notas.application.sharing.entities import get_or_create_entity_share_resource
from notas.application.sharing.services import create_share_invitation
from notas.domain.models import InboxItem, Meal, Program, ShareClaim, ShareResource

User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class NormalizedShareCompatibilityTests(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user(
            username="sender", email="sender@test.com", password="12345678"
        )
        self.recipient = User.objects.create_user(
            username="recipient", email="recipient@test.com", password="12345678"
        )
        EmailAddress.objects.create(user=self.recipient, email=self.recipient.email, verified=True, primary=True)
        self.meal = Meal.objects.create(name="Shared meal", created_by=self.sender, is_draft=False)
        self.meal_resource = get_or_create_entity_share_resource(
            sender=self.sender,
            subject_type=ShareResource.SubjectType.MEAL,
            subject_id=self.meal.id,
        ).resource
        self.meal_invitation = create_share_invitation(
            resource=self.meal_resource,
            sender=self.sender,
            recipient_email=self.recipient.email,
        )
        self.program = Program.objects.create(name="Shared program", created_by=self.sender)
        self.program_resource = get_or_create_entity_share_resource(
            sender=self.sender,
            subject_type=ShareResource.SubjectType.PROGRAM,
            subject_id=self.program.id,
        ).resource
        self.program_invitation = create_share_invitation(
            resource=self.program_resource,
            sender=self.sender,
            recipient_email=self.recipient.email,
        )
        self.client = Client()

    def test_legacy_named_get_route_only_redirects_to_preview(self):
        response = self.client.get(reverse("meal_share_accept", args=[self.meal_invitation.public_id]))

        self.assertRedirects(
            response,
            reverse("share_invitation_preview", args=[self.meal_invitation.public_id]),
            fetch_redirect_response=False,
        )
        self.assertFalse(ShareClaim.objects.exists())
        self.assertFalse(InboxItem.objects.exists())

    def test_explicit_post_claim_is_recipient_bound_and_idempotent(self):
        claim_url = reverse("share_invitation_claim", args=[self.meal_invitation.public_id])
        attacker = User.objects.create_user(
            username="attacker", email="attacker@test.com", password="12345678"
        )
        EmailAddress.objects.create(user=attacker, email=attacker.email, verified=True, primary=True)
        self.client.force_login(attacker)
        self.assertEqual(self.client.post(claim_url).status_code, 409)

        self.client.force_login(self.recipient)
        self.assertEqual(self.client.post(claim_url).status_code, 302)
        self.assertEqual(self.client.post(claim_url).status_code, 302)
        self.assertEqual(ShareClaim.objects.filter(resource=self.meal_resource).count(), 1)
        self.assertEqual(InboxItem.objects.filter(resource=self.meal_resource).count(), 1)

    def test_program_compatibility_route_uses_same_secure_preview(self):
        response = self.client.get(
            reverse("program_share_accept", args=[self.program_invitation.public_id])
        )

        self.assertRedirects(
            response,
            reverse("share_invitation_preview", args=[self.program_invitation.public_id]),
            fetch_redirect_response=False,
        )
        self.assertFalse(ShareClaim.objects.filter(resource=self.program_resource).exists())
