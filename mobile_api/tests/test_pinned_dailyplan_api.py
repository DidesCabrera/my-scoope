from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from mobile_api.selectors import today_payload
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood, PinnedDailyPlan


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIPinnedDailyPlanTests(AuthenticatedMobileAPITestCase):
    def test_pinned_dailyplan_stays_live_and_tracks_each_day_without_duplicates(self):
        first = self.client.post("/api/v1/today/pinned-plan", data={}, content_type="application/json")
        second = self.client.post("/api/v1/today/pinned-plan", data={}, content_type="application/json")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        plan_id = first.json()["data"]["pinned_plan"]["id"]
        self.assertEqual(second.json()["data"]["pinned_plan"]["id"], plan_id)
        self.assertTrue(first.json()["data"]["pinned_plan"]["name"].startswith("Mis comidas del "))
        self.assertEqual(PinnedDailyPlan.objects.filter(user=self.user).count(), 1)

        meal = Meal.objects.create(name="Comida fija", created_by=self.user, is_draft=False)
        food = Food.objects.create(name="Alimento fijo", created_by=self.user, protein=10, carbs=20, fat=5)
        meal_food = MealFood.objects.create(meal=meal, food=food, quantity=100)
        relation = DailyPlanMeal.objects.create(dailyplan_id=plan_id, meal=meal)
        today = self.client.get("/api/v1/today").json()["data"]
        meal_key = f"dailyplan-meal:{relation.id}"
        food_key = f"meal-food:{meal_food.id}"

        self.assertEqual(today["pinned_plan"]["panel"]["meals"][0]["name"], "Comida fija")
        completed = self.client.post(
            f"/api/v1/today/pinned-plan/meals/{meal_key}/check-ins",
            data={"action": "completed", "idempotency_key": "pinned-meal-completed-1"},
            content_type="application/json",
        )
        prepared = self.client.post(
            f"/api/v1/today/pinned-plan/meals/{meal_key}/check-ins",
            data={"action": "food_prepared", "food_snapshot_key": food_key, "idempotency_key": "pinned-food-prepared-1"},
            content_type="application/json",
        )

        self.assertEqual(completed.status_code, 200)
        self.assertEqual(prepared.status_code, 200)
        execution = prepared.json()["data"]["meal_execution"][0]
        self.assertEqual(execution["status"], "completed")
        self.assertEqual(execution["prepared_food_keys"], [food_key])

        another_day = today_payload(self.user, now=timezone.now() + timedelta(days=2))

        self.assertEqual(another_day["meal_execution"][0]["status"], "planned")
        self.assertEqual(another_day["meal_execution"][0]["prepared_food_keys"], [])

    def test_pinning_reuses_library_plan_and_replaces_the_previous_choice(self):
        first = DailyPlan.objects.create(name="Plan uno", created_by=self.user, is_draft=False)
        second = DailyPlan.objects.create(name="Plan dos", created_by=self.user, is_draft=False)

        response = self.client.put(
            "/api/v1/today/pinned-plan",
            data={"dailyplan_id": first.id},
            content_type="application/json",
        )
        replaced = self.client.put(
            "/api/v1/today/pinned-plan",
            data={"dailyplan_id": second.id},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(replaced.status_code, 200)
        self.assertEqual(replaced.json()["data"]["pinned_plan"]["id"], second.id)
        self.assertEqual(PinnedDailyPlan.objects.get(user=self.user).dailyplan_id, second.id)

        removed = self.client.delete("/api/v1/today/pinned-plan")

        self.assertEqual(removed.status_code, 200)
        self.assertIsNone(removed.json()["data"]["pinned_plan"])
        self.assertFalse(PinnedDailyPlan.objects.get(user=self.user).is_active)

        created = self.client.post("/api/v1/today/pinned-plan", data={}, content_type="application/json")

        self.assertEqual(created.status_code, 200)
        self.assertNotEqual(created.json()["data"]["pinned_plan"]["id"], second.id)
        self.assertEqual(PinnedDailyPlan.objects.filter(user=self.user).count(), 1)
        self.assertTrue(PinnedDailyPlan.objects.get(user=self.user).is_active)
