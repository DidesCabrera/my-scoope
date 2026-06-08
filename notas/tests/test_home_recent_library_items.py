from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood


User = get_user_model()


class HomeRecentLibraryItemsTests(TestCase):
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
        self.food = Food.objects.create(
            name="Chicken",
            protein=20,
            carbs=0,
            fat=3,
            created_by=self.user,
        )

    def _library_meal(self, name):
        meal = Meal.objects.create(
            name=name,
            created_by=self.user,
            is_draft=False,
        )
        MealFood.objects.create(
            meal=meal,
            food=self.food,
            quantity=100,
        )
        return meal

    def _library_dailyplan(self, name, meal):
        dailyplan = DailyPlan.objects.create(
            name=name,
            created_by=self.user,
            is_draft=False,
        )
        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal,
        )
        return dailyplan

    def test_home_recent_meals_match_personal_library_scope(self):
        visible_meal = self._library_meal("Visible library meal")

        Meal.objects.create(
            name="Draft empty meal",
            created_by=self.user,
            is_draft=True,
        )

        embedded_meal = self._library_meal("Embedded dailyplan meal")
        dailyplan = DailyPlan.objects.create(
            name="Container dailyplan",
            created_by=self.user,
            is_draft=False,
        )
        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=embedded_meal,
        )

        Meal.objects.create(
            name="Other user meal",
            created_by=self.other_user,
            is_draft=False,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse("home_view"))

        self.assertEqual(response.status_code, 200)

        recent_meal_names = [
            item["titulo"]["name"]
            for item in response.context["vm"]["content"]["meals"]["items"]
        ]

        self.assertIn(visible_meal.name, recent_meal_names)
        self.assertNotIn("Draft empty meal", recent_meal_names)
        self.assertNotIn(embedded_meal.name, recent_meal_names)
        self.assertNotIn("Other user meal", recent_meal_names)

    def test_home_recent_dailyplans_match_personal_library_scope(self):
        meal = self._library_meal("Plan meal")
        visible_dailyplan = self._library_dailyplan(
            "Visible library dailyplan",
            meal,
        )

        DailyPlan.objects.create(
            name="Draft empty dailyplan",
            created_by=self.user,
            is_draft=True,
        )

        DailyPlan.objects.create(
            name="Other user dailyplan",
            created_by=self.other_user,
            is_draft=False,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse("home_view"))

        self.assertEqual(response.status_code, 200)

        recent_dailyplan_names = [
            item["titulo"]["name"]
            for item in response.context["vm"]["content"]["dailyplans"]["items"]
        ]

        self.assertIn(visible_dailyplan.name, recent_dailyplan_names)
        self.assertNotIn("Draft empty dailyplan", recent_dailyplan_names)
        self.assertNotIn("Other user dailyplan", recent_dailyplan_names)