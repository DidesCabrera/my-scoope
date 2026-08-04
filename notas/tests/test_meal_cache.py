from django.contrib.auth import get_user_model
from django.test import TestCase

from notas.domain.models import Food, Meal, MealFood

User = get_user_model()


class MealCacheTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@test.com",
            password="12345678",
        )

    def test_meal_cache_recomputes_when_mealfood_is_created(self):
        meal = Meal.objects.create(
            name="Breakfast",
            created_by=self.user,
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
            quantity=90,
        )

        meal.refresh_from_db()

        self.assertIsNotNone(meal.protein_cached)
        self.assertIsNotNone(meal.carbs_cached)
        self.assertIsNotNone(meal.fat_cached)
        self.assertIsNotNone(meal.total_kcal_cached)
        self.assertIsNotNone(meal.foods_aggregation_cached)

        self.assertGreater(meal.protein_cached, 0)
        self.assertGreater(meal.total_kcal_cached, 0)

    def test_meal_cache_recomputes_when_mealfood_is_deleted(self):
        meal = Meal.objects.create(
            name="Breakfast",
            created_by=self.user,
        )

        food = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        meal_food = MealFood.objects.create(
            meal=meal,
            food=food,
            quantity=90,
        )

        meal.refresh_from_db()
        self.assertGreater(meal.total_kcal_cached, 0)

        meal_food.delete()

        meal.refresh_from_db()

        self.assertEqual(meal.protein_cached, 0)
        self.assertEqual(meal.carbs_cached, 0)
        self.assertEqual(meal.fat_cached, 0)
        self.assertEqual(meal.total_kcal_cached, 0)