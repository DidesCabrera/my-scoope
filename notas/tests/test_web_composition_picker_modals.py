from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from notas.domain.models import DailyPlan, Meal, Program

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
        self.assertContains(response, 'data-scope="meal-result"')
        self.assertContains(response, 'class="entity-card card picker-result-card picker-result-card--meal"')
        self.assertContains(response, 'data-role="result-foods-grid"')
        self.assertContains(response, 'data-target="#card-grid-foods-picker-result-meal"')
        self.assertNotContains(response, 'class="preview-picker"')
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
        self.assertContains(response, 'data-scope="day-preview"')
        self.assertContains(response, 'class="entity-card card picker-result-card picker-result-card--dailyplan"')
        self.assertContains(response, 'data-role="result-meals-grid"')
        self.assertContains(response, 'data-target="#card-grid-meals-picker-result-dailyplan"')
        self.assertNotContains(response, 'class="preview-picker"')
        self.assertContains(
            response,
            reverse("create_meal_for_dailyplan", args=[dailyplan.id]),
        )
        self.assertNotContains(response, 'id="dailyplan-picker-section" class="section_picker')

    def test_owned_program_uses_two_step_dailyplan_dialog_with_week_projection(self):
        program = Program.objects.create(
            name="Editable program",
            created_by=self.user,
            duration_weeks=1,
        )
        DailyPlan.objects.create(
            name="Available daily plan",
            created_by=self.user,
            is_draft=False,
        )

        response = self.client.get(reverse("program_detail", args=[program.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<dialog\n  id="program-slot-picker-section"')
        self.assertContains(response, "data-picker-modal")
        self.assertContains(response, 'data-picker-step-panel="selection"')
        self.assertContains(response, "1. Selecciona un plan diario")
        self.assertContains(response, 'data-picker-step-panel="impact"')
        self.assertContains(response, "2. Configura y revisa el impacto")
        self.assertContains(response, "Resultado proyectado")
        self.assertContains(response, "js-program-slot-projection")
        self.assertContains(response, "composition-picker-fixed-configuration")
        self.assertContains(response, 'data-program-week-rows="')
        self.assertContains(response, 'data-day-number="1"')
        self.assertContains(response, '<script type="module" src="/static/notas/js/program_slot_picker.js"></script>')
        self.assertNotContains(response, 'class="program-slot-picker section_picker')
