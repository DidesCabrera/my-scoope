from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notas.domain.models import Profile, WeightLog


User = get_user_model()


class ProfileSectionsTests(TestCase):
    def _completed_user(self, username="profile_user"):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@test.com",
            password="12345678",
        )
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
        WeightLog.objects.create(
            user=user,
            date=timezone.localdate(),
            weight_kg=88.5,
            source=WeightLog.SOURCE_ONBOARDING,
        )
        return user

    def test_profile_detail_only_renders_account_information(self):
        user = self._completed_user("profile_sections")
        self.client.force_login(user)

        response = self.client.get(reverse("profile_detail"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "home-eyebrow")
        self.assertNotContains(response, "profile-account-subtitle")
        self.assertContains(response, "Información de cuenta")
        self.assertContains(response, '<section class="profile-section-card profile-section-card--account" id="profile-account">')
        self.assertNotContains(response, "Perfil nutricional")
        self.assertNotContains(response, "Uso comercial")
        self.assertNotContains(response, "Métricas corporales")

    def test_profile_nutrition_renders_personal_data_and_body_metrics(self):
        user = self._completed_user("profile_nutrition_sections")
        self.client.force_login(user)

        response = self.client.get(reverse("profile_nutrition"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "home-eyebrow")
        self.assertNotContains(response, "profile-account-subtitle")
        self.assertContains(response, "Perfil nutricional")
        self.assertContains(response, "Métricas corporales")
        self.assertContains(response, "Contexto para propuestas")
        self.assertContains(response, "88.5 kg")
        self.assertContains(response, "188 cm")
        self.assertContains(response, "Masculino")
        self.assertContains(response, "Propuestas para terceros")
        self.assertNotContains(response, "<span>Onboarding</span>")
        self.assertNotContains(response, "Versión 1")
        self.assertContains(response, 'onclick="openProfileEditModal()"')
        self.assertContains(response, 'id="profileEditModal"')
        self.assertContains(response, 'class="modal hidden profile-edit-modal"')
        self.assertContains(response, "Editar ficha nutricional")
        self.assertNotContains(response, "Información de cuenta")
        self.assertNotContains(response, "Uso comercial")

    def test_profile_credits_only_renders_credit_usage(self):
        user = self._completed_user("profile_credit_sections")
        self.client.force_login(user)

        response = self.client.get(reverse("profile_credits"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "home-eyebrow")
        self.assertNotContains(response, "profile-account-subtitle")
        self.assertContains(response, "Uso comercial")
        self.assertContains(response, "Créditos disponibles")
        self.assertContains(response, '<section class="profile-section-card profile-section-card--billing" id="profile-credits">')
        self.assertNotContains(response, "Información de cuenta")
        self.assertNotContains(response, "Perfil nutricional")
        self.assertNotContains(response, "Métricas corporales")

    def test_profile_sidebar_links_to_distinct_sections(self):
        user = self._completed_user("profile_sidebar_links")
        self.client.force_login(user)

        response = self.client.get(reverse("profile_detail"))

        self.assertContains(response, f'href="{reverse("profile_detail")}"')
        self.assertContains(response, f'href="{reverse("profile_nutrition")}"')
        self.assertContains(response, f'href="{reverse("profile_credits")}"')
        self.assertNotContains(response, "#profile-personal")
        self.assertNotContains(response, "#profile-credits")

    def test_profile_nutrition_update_changes_stable_body_fields(self):
        user = self._completed_user("profile_update")
        self.client.force_login(user)

        response = self.client.post(
            reverse("profile_nutrition_update"),
            {
                "birth_date": "1990-05-10",
                "sex": Profile.SEX_FEMALE,
                "height_cm": "172",
            },
        )

        self.assertRedirects(response, reverse("profile_nutrition"))
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.birth_date, date(1990, 5, 10))
        self.assertEqual(user.profile.sex, Profile.SEX_FEMALE)
        self.assertEqual(user.profile.height_cm, 172)
        self.assertEqual(user.weight_logs.count(), 1)
        self.assertEqual(user.weight_logs.first().weight_kg, 88.5)

    def test_invalid_profile_nutrition_update_rerenders_with_errors(self):
        user = self._completed_user("profile_invalid")
        self.client.force_login(user)

        response = self.client.post(
            reverse("profile_nutrition_update"),
            {
                "birth_date": "2030-05-10",
                "sex": Profile.SEX_FEMALE,
                "height_cm": "172",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Revisa los datos de tu ficha nutricional")
        self.assertContains(response, "Ingresa una fecha de nacimiento anterior a hoy")
        self.assertContains(response, 'data-open-on-load="true"')
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.birth_date, date(1988, 1, 17))
        self.assertEqual(user.profile.sex, Profile.SEX_MALE)
        self.assertEqual(user.profile.height_cm, 188)
