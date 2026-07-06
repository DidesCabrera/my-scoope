from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from notas.domain.models import Profile


User = get_user_model()


class NutritionOnboardingGateTests(TestCase):
    def _user(self, username="gate_user", *, staff=False, superuser=False):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@test.com",
            password="12345678",
            is_staff=staff,
            is_superuser=superuser,
        )
        return user

    def _complete_onboarding(self, user):
        profile = user.profile
        profile.birth_date = date(1988, 1, 17)
        profile.sex = Profile.SEX_MALE
        profile.height_cm = 188
        profile.onboarding_completed_at = timezone.now()
        profile.onboarding_version = Profile.ONBOARDING_VERSION_NUTRITION_V1
        profile.save(
            update_fields=[
                "birth_date",
                "sex",
                "height_cm",
                "onboarding_completed_at",
                "onboarding_version",
            ]
        )

    def test_authenticated_user_without_onboarding_is_redirected_from_app(self):
        user = self._user("gate_incomplete")
        self.client.force_login(user)

        response = self.client.get(reverse("home_view"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("accounts:nutrition_onboarding"))

    def test_completed_user_can_access_app_home(self):
        user = self._user("gate_complete")
        self._complete_onboarding(user)
        self.client.force_login(user)

        response = self.client.get(reverse("home_view"))

        self.assertEqual(response.status_code, 200)

    def test_onboarding_route_does_not_redirect_to_itself(self):
        user = self._user("gate_onboarding")
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:nutrition_onboarding"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Completa tus datos iniciales")

    def test_staff_user_is_not_forced_through_onboarding(self):
        user = self._user("gate_staff", staff=True)
        self.client.force_login(user)

        response = self.client.get(reverse("home_view"))

        self.assertEqual(response.status_code, 200)

    def test_superuser_is_not_forced_through_onboarding(self):
        user = self._user("gate_super", staff=True, superuser=True)
        self.client.force_login(user)

        response = self.client.get(reverse("home_view"))

        self.assertEqual(response.status_code, 200)

    def test_gate_can_be_disabled_in_settings(self):
        user = self._user("gate_disabled")
        self.client.force_login(user)

        with override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False):
            response = self.client.get(reverse("home_view"))

        self.assertEqual(response.status_code, 200)
