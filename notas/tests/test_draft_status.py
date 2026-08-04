from django.contrib.auth import get_user_model
from django.test import TestCase

from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood

User = get_user_model()


class DraftStatusTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@test.com",
            password="12345678",
        )

    def test_meal_update_draft_status_sets_false_when_has_foods(self):
        meal = Meal.objects.create(
            name="Draft meal",
            created_by=self.user,
            is_draft=True,
        )

        food = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        MealFood.objects.create(
            meal=meal,
            food=food,
            quantity=100,
        )

        meal.update_draft_status()
        meal.refresh_from_db()

        self.assertFalse(meal.is_draft)

    def test_dailyplan_update_draft_status_sets_false_when_has_meals(self):
        meal = Meal.objects.create(
            name="Meal 1",
            created_by=self.user,
            is_draft=False,
        )

        dailyplan = DailyPlan.objects.create(
            name="Draft plan",
            created_by=self.user,
            is_draft=True,
        )

        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal,
            order=1,
        )

        dailyplan.update_draft_status()
        dailyplan.refresh_from_db()

        self.assertFalse(dailyplan.is_draft)