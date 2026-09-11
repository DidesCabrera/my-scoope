from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import resolve, reverse

from notas.domain.models import Meal, MealShare, Program, ProgramShare

User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MealShareTests(TestCase):

    def setUp(self):
        self.sender = User.objects.create_user(
            username="sender",
            email="sender@test.com",
            password="12345678",
        )
        self.recipient = User.objects.create_user(
            username="recipient",
            email="recipient@test.com",
            password="12345678",
        )

        self.meal = Meal.objects.create(
            name="Shared meal",
            created_by=self.sender,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        self.share = MealShare.objects.create(
            sender=self.sender,
            recipient_email=self.recipient.email,
            meal=self.meal,
        )
        self.program = Program.objects.create(name="Shared program", created_by=self.sender)
        self.program_share = ProgramShare.objects.create(
            sender=self.sender,
            recipient_email=self.recipient.email,
            program=self.program,
        )

        self.client = Client()


    def test_meal_share_dismiss_url_resolves_to_dismiss_view(self):
        match = resolve(reverse("meal_share_dismiss", args=[self.share.id]))

        self.assertEqual(match.url_name, "meal_share_dismiss")

    def test_meal_share_accept_sets_accepted_by(self):
        self.client.login(
            username="recipient",
            password="12345678",
        )

        response = self.client.get(
            reverse("meal_share_accept", args=[self.share.token])
        )

        self.assertEqual(response.status_code, 302)

        self.share.refresh_from_db()
        self.assertEqual(self.share.accepted_by, self.recipient)

    def test_share_token_does_not_allow_a_different_email_to_claim(self):
        attacker = User.objects.create_user(
            username="attacker",
            email="attacker@test.com",
            password="12345678",
        )
        self.client.force_login(attacker)

        response = self.client.get(reverse("meal_share_accept", args=[self.share.token]))

        self.assertEqual(response.status_code, 404)
        self.share.refresh_from_db()
        self.assertIsNone(self.share.accepted_by)

    def test_share_claim_is_idempotent_and_cannot_be_overwritten(self):
        self.share.accepted_by = self.recipient
        self.share.save(update_fields=["accepted_by"])
        duplicate_email_user = User.objects.create_user(
            username="duplicate-recipient",
            email=self.recipient.email.upper(),
            password="12345678",
        )
        self.client.force_login(duplicate_email_user)

        response = self.client.get(reverse("meal_share_accept", args=[self.share.token]))

        self.assertEqual(response.status_code, 404)
        self.share.refresh_from_db()
        self.assertEqual(self.share.accepted_by, self.recipient)

        self.client.force_login(self.recipient)
        response = self.client.get(reverse("meal_share_accept", args=[self.share.token]))
        self.assertEqual(response.status_code, 302)
        self.share.refresh_from_db()
        self.assertEqual(self.share.accepted_by, self.recipient)

    def test_program_share_has_a_recipient_bound_acceptance_route(self):
        self.client.force_login(self.recipient)

        response = self.client.get(reverse("program_share_accept", args=[self.program_share.token]))

        self.assertRedirects(response, reverse("inbox_list"))
        self.program_share.refresh_from_db()
        self.assertEqual(self.program_share.accepted_by, self.recipient)

    def test_meal_share_dismiss_sets_dismissed_true(self):
        self.share.accepted_by = self.recipient
        self.share.save(update_fields=["accepted_by"])

        self.client.login(
            username="recipient",
            password="12345678",
        )

        response = self.client.post(
            reverse("meal_share_dismiss", args=[self.share.id])
        )

        self.assertEqual(response.status_code, 302)

        self.share.refresh_from_db()
        self.assertTrue(self.share.dismissed)

    def test_meal_unshare_sets_removed_true(self):
        self.share.accepted_by = self.recipient
        self.share.save(update_fields=["accepted_by"])

        self.client.login(
            username="recipient",
            password="12345678",
        )

        response = self.client.post(
            reverse("meal_unshare", args=[self.share.id])
        )

        self.assertEqual(response.status_code, 302)

        self.share.refresh_from_db()
        self.assertTrue(self.share.removed)

    def test_meal_share_dismiss_requires_accepted_user(self):
        other_user = User.objects.create_user(
            username="other",
            email="other@test.com",
            password="12345678",
        )

        self.client.login(
            username="other",
            password="12345678",
        )

        response = self.client.post(
            reverse("meal_share_dismiss", args=[self.share.id])
        )

        self.assertEqual(response.status_code, 404)

    def test_meal_unshare_requires_accepted_user(self):
        other_user = User.objects.create_user(
            username="other2",
            email="other2@test.com",
            password="12345678",
        )

        self.client.login(
            username="other2",
            password="12345678",
        )

        response = self.client.post(
            reverse("meal_unshare", args=[self.share.id])
        )

        self.assertEqual(response.status_code, 404)
