from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from notas.domain.models import DailyPlan, Meal

User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class WebCompositionPickerModalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="picker-owner",
            email="picker-owner@test.com",
            password="12345678",
        )
        self.client = Client()
        self.client.login(username="picker-owner", password="12345678")

    def test_owned_meal_uses_two_step_food_dialog(self):
        meal = Meal.objects.create(
            name="Editable meal",
            created_by=self.user,
            is_draft=False,
        )

        response = self.client.get(reverse("meal_detail", args=[meal.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<dialog\n  id="meal-picker-section"')
        self.assertContains(response, "data-picker-modal")
        self.assertContains(response, 'data-picker-step-panel="selection"')
        self.assertContains(response, 'data-picker-step-panel="impact"')
        self.assertContains(response, "Crear alimento")
        self.assertContains(response, reverse("food_create"))
        self.assertNotContains(response, 'id="meal-picker-section" class="section_picker')

    def test_owned_dailyplan_uses_two_step_meal_dialog(self):
        dailyplan = DailyPlan.objects.create(
            name="Editable daily plan",
            created_by=self.user,
            is_draft=False,
        )

        response = self.client.get(reverse("dailyplan_detail", args=[dailyplan.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<dialog\n    id="dailyplan-picker-section"')
        self.assertContains(response, "data-picker-modal")
        self.assertContains(response, 'data-picker-step-panel="selection"')
        self.assertContains(response, 'data-picker-step-panel="impact"')
        self.assertContains(response, "Crear comida")
        self.assertContains(
            response,
            reverse("create_meal_for_dailyplan", args=[dailyplan.id]),
        )
        self.assertNotContains(response, 'id="dailyplan-picker-section" class="section_picker')
