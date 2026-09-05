from django.test import override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileCompositionProjectionAPITests(AuthenticatedMobileAPITestCase):
    def test_food_picker_replaces_the_owned_relation_and_projects_the_result(self):
        original = Food.objects.create(
            name="Avena original", protein=10, carbs=60, fat=5, created_by=self.user
        )
        replacement = Food.objects.create(
            name="Yogur de reemplazo", protein=12, carbs=8, fat=3, created_by=self.user
        )
        meal = Meal.objects.create(name="Comida editable", created_by=self.user, is_draft=False)
        relation = MealFood.objects.create(meal=meal, food=original, quantity=50)
        payload = {"food_id": replacement.id, "meal_food_id": relation.id, "quantity": 80}

        preview = self.client.post(
            f"/api/v1/library/meals/{meal.id}/food-picker/preview",
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(preview.status_code, 200)
        projected = preview.json()["data"]["result"]["panel"]["foods"]
        self.assertEqual(len(projected), 1)
        self.assertEqual(projected[0]["relation_id"], relation.id)
        self.assertEqual(projected[0]["projected_label"], "Reemplazo")
        self.assertEqual(projected[0]["name"], "Yogur de reemplazo")

        dailyplan = DailyPlan.objects.create(name="Plan del DPM", created_by=self.user, is_draft=False)
        dailyplan_meal = DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=meal)
        contextual_preview = self.client.post(
            f"/api/v1/library/meals/{meal.id}/food-picker/preview",
            data={**payload, "dailyplan_id": dailyplan.id, "dailyplan_meal_id": dailyplan_meal.id},
            content_type="application/json",
        )
        self.assertEqual(contextual_preview.status_code, 200)
        contextual_result = contextual_preview.json()["data"]["result"]
        self.assertEqual(contextual_result["entity"], "dailyPlan")
        self.assertEqual(contextual_result["id"], dailyplan.id)
        self.assertEqual(contextual_result["panel"]["kind"], "meals")
        projected_meal = contextual_result["panel"]["meals"][0]
        self.assertEqual(projected_meal["relation_id"], dailyplan_meal.id)
        self.assertEqual(projected_meal["projected_label"], "Actualizada")
        self.assertEqual(projected_meal["foods"][0]["name"], "Yogur de reemplazo")

        commit = self.client.post(
            f"/api/v1/library/meals/{meal.id}/food-picker/commit",
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(commit.status_code, 200)
        relation.refresh_from_db()
        self.assertEqual(relation.id, commit.json()["data"]["created_id"])
        self.assertEqual(relation.food_id, replacement.id)
        self.assertEqual(float(relation.quantity), 80)
        self.assertEqual(MealFood.objects.filter(meal=meal).count(), 1)
