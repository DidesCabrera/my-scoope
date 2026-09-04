import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from notas.domain.models import DailyPlan, DailyPlanMeal, Meal

User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class DailyPlanMealPickerTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@test.com",
            password="12345678",
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@test.com",
            password="12345678",
        )

        self.client = Client()
        self.client.login(
            username="felipe",
            password="12345678",
        )

        self.dailyplan = DailyPlan.objects.create(
            name="Plan 1",
            created_by=self.user,
            is_draft=False,
        )

    def test_dailyplan_detail_picker_browse_meals_should_only_include_current_user_library_meals(self):
        self.library_meal = Meal.objects.create(
            name="Library meal",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        Meal.objects.create(
            name="Draft meal",
            created_by=self.user,
            is_draft=True,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        self.dpm_meal = Meal.objects.create(
            name="DPM meal",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=self.dpm_meal,
            order=1,
        )

        Meal.objects.create(
            name="Other user meal",
            created_by=self.other_user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        response = self.client.get(
            reverse("dailyplan_detail", args=[self.dailyplan.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("meal_picker_data_json", response.context)

        payload = json.loads(response.context["meal_picker_data_json"])
        browse_meals = payload["browse_meals"]
        browse_names = [meal["name"] for meal in browse_meals]

        self.assertIn("Library meal", browse_names)
        self.assertNotIn("Draft meal", browse_names)
        self.assertNotIn("DPM meal", browse_names)
        self.assertNotIn("Other user meal", browse_names)

    def test_dailyplan_detail_picker_payload_has_expected_shape(self):
        Meal.objects.create(
            name="Library meal",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        response = self.client.get(
            reverse("dailyplan_detail", args=[self.dailyplan.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("meal_picker_data_json", response.context)

        payload = json.loads(response.context["meal_picker_data_json"])

        self.assertIsInstance(payload, dict)
        self.assertIn("browse_meals", payload)
        self.assertIn("existing_meals", payload)
        self.assertIsInstance(payload["browse_meals"], list)
        self.assertIsInstance(payload["existing_meals"], list)

    def test_dailyplan_detail_picker_includes_current_user_library_meal_id(self):
        self.library_meal = Meal.objects.create(
            name="Visible meal",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        response = self.client.get(
            reverse("dailyplan_detail", args=[self.dailyplan.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("meal_picker_data_json", response.context)

        payload = json.loads(response.context["meal_picker_data_json"])
        browse_meals = payload["browse_meals"]
        browse_ids = [meal["id"] for meal in browse_meals]
        browse_names = [meal["name"] for meal in browse_meals]

        self.assertIn(self.library_meal.id, browse_ids)
        self.assertIn("Visible meal", browse_names)

    def test_dailyplan_detail_picker_existing_meals_includes_dailyplan_meals(self):
        self.dpm_meal = Meal.objects.create(
            name="DPM meal",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        dailyplan_meal = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=self.dpm_meal,
            order=1,
        )

        response = self.client.get(
            reverse("dailyplan_detail", args=[self.dailyplan.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("meal_picker_data_json", response.context)

        payload = json.loads(response.context["meal_picker_data_json"])
        existing_meals = payload["existing_meals"]
        existing_names = [meal["name"] for meal in existing_meals]

        self.assertIn("DPM meal", existing_names)

        picker_context = json.loads(response.context["meal_picker_context"])
        self.assertEqual(picker_context["dailyplan"]["name"], self.dailyplan.name)
        self.assertEqual(
            picker_context["dailyplan"]["meals"],
            [
                {
                    "dailyplanmeal_id": dailyplan_meal.id,
                    "meal_id": self.dpm_meal.id,
                    "name": "DPM meal",
                    "hour": "",
                    "note": "",
                }
            ],
        )
