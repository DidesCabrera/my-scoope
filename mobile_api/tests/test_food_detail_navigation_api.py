from django.contrib.auth.models import User
from django.test import override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood, Program, ProgramDay


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class FoodDetailNavigationAPITests(AuthenticatedMobileAPITestCase):
    def test_composition_payloads_expose_the_food_detail_id_at_every_level(self):
        food = Food.objects.create(name="Avena navegable", protein=10, carbs=20, fat=5, created_by=self.user)
        meal = Meal.objects.create(name="Comida navegable", created_by=self.user, is_draft=False)
        MealFood.objects.create(meal=meal, food=food, quantity=100)
        dailyplan = DailyPlan.objects.create(name="Plan navegable", created_by=self.user, is_draft=False)
        DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=meal)
        program = Program.objects.create(name="Programa navegable", created_by=self.user, duration_weeks=1)
        ProgramDay.objects.create(program=program, dailyplan=dailyplan, week_number=1, day_number=1)

        meal_data = self.client.get(f"/api/v1/library/meals/{meal.id}").json()["data"]
        dailyplan_data = self.client.get(f"/api/v1/library/daily-plans/{dailyplan.id}").json()["data"]
        program_data = self.client.get(f"/api/v1/library/programs/{program.id}").json()["data"]

        self.assertEqual(meal_data["panel"]["foods"][0]["detail_id"], food.id)
        self.assertEqual(dailyplan_data["panel"]["meals"][0]["foods"][0]["detail_id"], food.id)
        self.assertEqual(dailyplan_data["panel"]["foods"][0]["detail_id"], food.id)
        week = program_data["panel"]["weeks"][0]
        self.assertEqual(week["days"][0]["meals"][0]["foods"][0]["detail_id"], food.id)
        self.assertEqual(week["foods"][0]["detail_id"], food.id)

    def test_readable_global_food_opens_without_owner_actions(self):
        global_food = Food.objects.create(name="Alimento global", protein=2, carbs=3, fat=1, is_global=True)
        other = User.objects.create_user(username="other-food-owner")
        private_food = Food.objects.create(name="Alimento privado", protein=1, carbs=1, fat=1, created_by=other)

        response = self.client.get(f"/api/v1/library/foods/{global_food.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["creator"], "Myscoope")
        self.assertEqual(response.json()["data"]["actions"], [])
        self.assertEqual(self.client.get(f"/api/v1/library/foods/{private_food.id}").status_code, 404)
