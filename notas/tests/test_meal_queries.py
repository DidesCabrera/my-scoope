from django.test import TestCase

from core.tests.builders import create_test_user
from notas.application.queries.meal_queries import (
    get_meal_detail,
    list_available_meals,
    list_user_meals,
    search_meals,
)
from notas.domain.models import MealShare
from notas.tests.builders import attach_food, create_food, create_meal


class MealQueryTests(TestCase):
    def setUp(self):
        self.user = create_test_user("felipe", password="pass123")
        self.other_user = create_test_user("other", password="pass123")

        self.egg = create_food(created_by=self.user, name="Egg", protein=13, carbs=1, fat=11)
        self.rice = create_food(created_by=self.user, name="Rice", protein=2.7, carbs=28, fat=0.3)
        self.user_meal = create_meal(created_by=self.user, name="Breakfast")
        attach_food(meal=self.user_meal, food=self.egg, quantity=100, order=1)
        attach_food(meal=self.user_meal, food=self.rice, quantity=200, order=2)

        self.public_meal = create_meal(
            name="Public Meal",
            created_by=self.other_user,
            is_public=True,
            is_forkable=True,
        )
        self.private_other_meal = create_meal(created_by=self.other_user, name="Private Other Meal")
        self.shared_meal = create_meal(created_by=self.other_user, name="Shared Meal")

        MealShare.objects.create(
            meal=self.shared_meal,
            sender=self.other_user,
            recipient_email="felipe@example.com",
            accepted_by=self.user,
        )

    def test_list_user_meals_returns_only_user_meals(self):
        meals = list_user_meals(self.user)

        names = [meal.name for meal in meals]

        self.assertEqual(names, ["Breakfast"])
        self.assertNotIn("Public Meal", names)
        self.assertNotIn("Private Other Meal", names)
        self.assertNotIn("Shared Meal", names)

    def test_list_available_meals_includes_public_and_shared(self):
        meals = list_available_meals(self.user)

        names = [meal.name for meal in meals]

        self.assertIn("Breakfast", names)
        self.assertIn("Public Meal", names)
        self.assertIn("Shared Meal", names)
        self.assertNotIn("Private Other Meal", names)

    def test_search_meals_filters_available_meals(self):
        meals = search_meals(self.user, "public")

        names = [meal.name for meal in meals]

        self.assertEqual(names, ["Public Meal"])

    def test_get_meal_detail_returns_serializable_dto(self):
        meal = get_meal_detail(
            self.user,
            self.user_meal.id,
        )

        data = meal.as_dict()

        self.assertEqual(data["id"], self.user_meal.id)
        self.assertEqual(data["name"], "Breakfast")
        self.assertEqual(data["foods_count"], 2)
        self.assertEqual(len(data["foods"]), 2)
        self.assertEqual(data["foods"][0]["food_name"], "Egg")
        self.assertEqual(data["foods"][0]["quantity"], 100.0)
        self.assertIn("total_kcal", data["kpis"])
        self.assertIn("alloc_protein", data["kpis"])

    def test_get_meal_detail_allows_public_meal(self):
        meal = get_meal_detail(
            self.user,
            self.public_meal.id,
        )

        self.assertEqual(meal.name, "Public Meal")

    def test_get_meal_detail_allows_shared_meal(self):
        meal = get_meal_detail(
            self.user,
            self.shared_meal.id,
        )

        self.assertEqual(meal.name, "Shared Meal")

    def test_get_meal_detail_blocks_private_other_meal(self):
        with self.assertRaises(Exception):
            get_meal_detail(
                self.user,
                self.private_other_meal.id,
            )
