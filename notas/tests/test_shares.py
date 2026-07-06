from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import resolve, reverse

from notas.domain.models import Meal, MealShare


User = get_user_model()


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