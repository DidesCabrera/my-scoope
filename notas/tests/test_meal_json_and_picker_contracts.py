import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from notas.application.queries.performance.meal_queries import meals_with_kcal
from notas.presentation.composition.js.meal_picker_builder import (
    build_meal_picker_meals_payload,
)
from notas.domain.models import Food, Meal, MealFood


User = get_user_model()


class MealJsonAndPickerContractTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@test.com",
            password="12345678",
        )

        self.client = Client()
        self.client.login(
            username="felipe",
            password="12345678",
        )

    def test_build_meal_picker_meals_payload_returns_expected_keys(self):
        meal = Meal.objects.create(
            name="Breakfast",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        payload = build_meal_picker_meals_payload([meal]).as_list()

        self.assertEqual(len(payload), 1)

        item = payload[0]

        self.assertIn("id", item)
        self.assertIn("name", item)
        self.assertIn("total_kcal", item)
        self.assertIn("protein", item)
        self.assertIn("carbs", item)
        self.assertIn("fat", item)
        self.assertIn("alloc", item)
        self.assertIn("foods", item)

    def test_build_meal_picker_meals_payload_reflects_cached_values(self):
        meal = Meal.objects.create(
            name="Breakfast",
            created_by=self.user,
            is_draft=False,
            protein_cached=20,
            carbs_cached=30,
            fat_cached=10,
            total_kcal_cached=290,
            alloc_protein_cached=27.5,
            alloc_carbs_cached=41.3,
            alloc_fat_cached=31.2,
            foods_aggregation_cached=[
                {"name": "Egg", "quantity": 100},
            ],
        )

        payload = build_meal_picker_meals_payload([meal]).as_list()

        item = payload[0]

        self.assertEqual(item["id"], meal.id)
        self.assertEqual(item["name"], "Breakfast")
        self.assertEqual(item["protein"], 20)
        self.assertEqual(item["carbs"], 30)
        self.assertEqual(item["fat"], 10)
        self.assertEqual(item["total_kcal"], 290)

        self.assertEqual(item["alloc"]["protein"], 27.5)
        self.assertEqual(item["alloc"]["carbs"], 41.3)
        self.assertEqual(item["alloc"]["fat"], 31.2)

        self.assertEqual(item["foods"], [{"name": "Egg", "quantity": 100}])

    def test_build_meal_picker_meals_payload_is_json_serializable(self):
        meal = Meal.objects.create(
            name="Breakfast",
            created_by=self.user,
            is_draft=False,
            protein_cached=20,
            carbs_cached=30,
            fat_cached=10,
            total_kcal_cached=290,
            alloc_protein_cached=27.5,
            alloc_carbs_cached=41.3,
            alloc_fat_cached=31.2,
            foods_aggregation_cached=[
                {"name": "Egg", "quantity": 100},
            ],
        )

        payload = build_meal_picker_meals_payload([meal]).as_list()

        serialized = json.dumps(payload)

        self.assertIn("Breakfast", serialized)
        self.assertIn("Egg", serialized)

    def test_meals_with_kcal_includes_meal_with_computed_cache_values(self):
        meal = Meal.objects.create(
            name="Breakfast",
            created_by=self.user,
            is_draft=False,
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

        meal.refresh_from_db()

        qs = meals_with_kcal().filter(id=meal.id)
        meal_from_qs = qs.get()

        self.assertEqual(meal_from_qs.id, meal.id)

    def test_meal_picker_payload_keeps_order_of_input_queryset(self):
        meal_a = Meal.objects.create(
            name="Meal A",
            created_by=self.user,
            is_draft=False,
        )
        meal_b = Meal.objects.create(
            name="Meal B",
            created_by=self.user,
            is_draft=False,
        )
        meal_c = Meal.objects.create(
            name="Meal C",
            created_by=self.user,
            is_draft=False,
        )

        ordered_meals = [meal_c, meal_a, meal_b]

        payload = build_meal_picker_meals_payload(ordered_meals).as_list()
        names = [item["name"] for item in payload]

        self.assertEqual(names, ["Meal C", "Meal A", "Meal B"])