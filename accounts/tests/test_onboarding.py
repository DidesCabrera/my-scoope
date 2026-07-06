from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notas.domain.models import Profile, WeightLog


User = get_user_model()


class NutritionOnboardingViewTests(TestCase):
    def test_requires_login(self):
        response = self.client.get(reverse("accounts:nutrition_onboarding"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_get_renders_slides_and_form(self):
        user = User.objects.create_user(
            username="onboarding_get",
            email="onboarding_get@test.com",
            password="12345678",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:nutrition_onboarding"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bienvenido a My Scoope")
        self.assertContains(response, "Tus librerías son reutilizables")
        self.assertContains(response, "La AI propone, tú apruebas")
        self.assertContains(response, "Completa tus datos iniciales")
        self.assertContains(response, "Fecha de nacimiento")

    def test_post_updates_profile_and_creates_initial_weight_metric(self):
        user = User.objects.create_user(
            username="onboarding_post",
            email="onboarding_post@test.com",
            password="12345678",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:nutrition_onboarding"),
            {
                "birth_date": "1988-01-17",
                "sex": Profile.SEX_MALE,
                "height_cm": "188",
                "weight_kg": "88.5",
            },
        )

        self.assertRedirects(response, reverse("home_view"))
        profile = user.profile
        profile.refresh_from_db()
        self.assertEqual(profile.birth_date, date(1988, 1, 17))
        self.assertEqual(profile.sex, Profile.SEX_MALE)
        self.assertEqual(profile.height_cm, 188)
        self.assertIsNotNone(profile.onboarding_completed_at)
        self.assertEqual(profile.onboarding_version, Profile.ONBOARDING_VERSION_NUTRITION_V1)

        weight_log = user.weight_logs.get()
        self.assertEqual(weight_log.weight_kg, 88.5)
        self.assertEqual(weight_log.source, WeightLog.SOURCE_ONBOARDING)
        self.assertEqual(weight_log.date, timezone.localdate())

    def test_invalid_post_keeps_form_slide_active(self):
        user = User.objects.create_user(
            username="onboarding_invalid",
            email="onboarding_invalid@test.com",
            password="12345678",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:nutrition_onboarding"),
            {
                "birth_date": "2030-01-17",
                "sex": Profile.SEX_MALE,
                "height_cm": "188",
                "weight_kg": "88.5",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-initial-step="3"')
        self.assertContains(response, "Ingresa una fecha de nacimiento anterior a hoy")
        self.assertEqual(user.weight_logs.count(), 0)
