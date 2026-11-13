from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.queries.global_food_queries import (
    DEFAULT_GLOBAL_FOOD_LIMIT,
    MAX_GLOBAL_FOOD_LIMIT,
    get_visible_global_food_queryset,
    list_global_foods,
    search_global_foods,
)
from notas.domain.models import Food, FoodAlias, FoodSourceMetadata


class GlobalFoodQueryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            password="pass123",
        )

        self.core_verified_oats = Food.objects.create(
            name="Oats, raw",
            canonical_name="oats raw",
            protein=16.9,
            carbs=66.3,
            fat=6.9,
            created_by=None,
            is_global=True,
            is_verified=True,
            is_active=True,
            food_group="cereals",
            food_subgroup="oats",
            visibility=Food.VISIBILITY_CORE,
            data_quality_score=90,
        )

        FoodSourceMetadata.objects.create(
            food=self.core_verified_oats,
            source=FoodSourceMetadata.SOURCE_USDA,
            source_food_id="1001",
            source_dataset="foundation_foods",
            source_version="2026-04",
        )

        FoodAlias.objects.create(
            food=self.core_verified_oats,
            name="Avena",
            normalized_name="avena",
            language="es",
            country="CL",
        )

        self.extended_chicken = Food.objects.create(
            name="Chicken breast, cooked",
            canonical_name="chicken breast cooked",
            protein=31,
            carbs=0,
            fat=3.6,
            created_by=None,
            is_global=True,
            is_verified=False,
            is_active=True,
            food_group="poultry_products",
            food_subgroup="",
            visibility=Food.VISIBILITY_EXTENDED,
            data_quality_score=75,
        )

        self.hidden_banana = Food.objects.create(
            name="Bananas, raw",
            canonical_name="bananas raw",
            protein=1.09,
            carbs=22.8,
            fat=0.33,
            created_by=None,
            is_global=True,
            is_verified=False,
            is_active=True,
            visibility=Food.VISIBILITY_HIDDEN,
            data_quality_score=60,
        )

        self.rejected_food = Food.objects.create(
            name="Rejected food",
            canonical_name="rejected food",
            protein=1,
            carbs=1,
            fat=1,
            created_by=None,
            is_global=True,
            is_verified=False,
            is_active=True,
            visibility=Food.VISIBILITY_REJECTED,
            data_quality_score=0,
        )

        self.inactive_food = Food.objects.create(
            name="Inactive global food",
            canonical_name="inactive global food",
            protein=1,
            carbs=1,
            fat=1,
            created_by=None,
            is_global=True,
            is_verified=True,
            is_active=False,
            visibility=Food.VISIBILITY_CORE,
            data_quality_score=90,
        )

        self.user_food = Food.objects.create(
            name="User oats custom",
            canonical_name="user oats custom",
            protein=10,
            carbs=20,
            fat=5,
            created_by=self.user,
            is_global=False,
            is_verified=False,
            is_active=True,
            visibility=Food.VISIBILITY_CORE,
            data_quality_score=90,
        )

    def test_get_visible_global_food_queryset_returns_core_and_extended_by_default(self):
        foods = list(get_visible_global_food_queryset())

        self.assertIn(self.core_verified_oats, foods)
        self.assertIn(self.extended_chicken, foods)
        self.assertNotIn(self.hidden_banana, foods)
        self.assertNotIn(self.rejected_food, foods)
        self.assertNotIn(self.inactive_food, foods)
        self.assertNotIn(self.user_food, foods)

    def test_get_visible_global_food_queryset_can_exclude_extended(self):
        foods = list(
            get_visible_global_food_queryset(
                include_extended=False,
            )
        )

        self.assertIn(self.core_verified_oats, foods)
        self.assertNotIn(self.extended_chicken, foods)

    def test_list_global_foods_returns_serializable_dto(self):
        result = list_global_foods()

        data = result.as_dict()

        self.assertEqual(data["count"], 2)
        self.assertEqual(data["limit"], DEFAULT_GLOBAL_FOOD_LIMIT)
        self.assertIsNone(data["search"])
        self.assertTrue(data["include_extended"])

        first_food = data["foods"][0]

        self.assertIn("id", first_food)
        self.assertIn("name", first_food)
        self.assertIn("canonical_name", first_food)
        self.assertIn("food_group", first_food)
        self.assertIn("visibility", first_food)
        self.assertIn("is_verified", first_food)
        self.assertIn("data_quality_score", first_food)
        self.assertIn("protein", first_food)
        self.assertIn("carbs", first_food)
        self.assertIn("fat", first_food)
        self.assertIn("total_kcal", first_food)
        self.assertIn("source", first_food)

    def test_list_global_foods_orders_core_before_extended(self):
        result = list_global_foods()

        names = [
            food.name
            for food in result.foods
        ]

        self.assertEqual(
            names,
            [
                "Oats, raw",
                "Chicken breast, cooked",
            ],
        )

    def test_list_global_foods_searches_by_name(self):
        result = list_global_foods(
            search="chicken",
        )

        names = [
            food.name
            for food in result.foods
        ]

        self.assertEqual(names, ["Chicken breast, cooked"])

    def test_list_global_foods_searches_by_canonical_name(self):
        result = list_global_foods(
            search="oats raw",
        )

        names = [
            food.name
            for food in result.foods
        ]

        self.assertEqual(names, ["Oats, raw"])

    def test_list_global_foods_searches_by_alias(self):
        result = list_global_foods(
            search="avena",
        )

        names = [
            food.name
            for food in result.foods
        ]

        self.assertEqual(names, ["Oats, raw"])

    def test_list_global_foods_normalizes_accented_or_punctuated_alias_search(self):
        for search in ("Avéna", "Avena,"):
            with self.subTest(search=search):
                self.assertEqual(
                    [food.name for food in search_global_foods(search=search)],
                    ["Oats, raw"],
                )

    def test_search_global_foods_returns_items(self):
        foods = search_global_foods(
            search="oats",
        )

        self.assertEqual(len(foods), 1)
        self.assertEqual(foods[0].name, "Oats, raw")

    def test_list_global_foods_strips_empty_search(self):
        result = list_global_foods(
            search="   ",
        )

        self.assertIsNone(result.search)
        self.assertEqual(result.count, 2)

    def test_list_global_foods_respects_limit(self):
        result = list_global_foods(
            limit=1,
        )

        self.assertEqual(result.count, 1)
        self.assertEqual(result.limit, 1)

    def test_list_global_foods_normalizes_invalid_limit(self):
        result = list_global_foods(
            limit=0,
        )

        self.assertEqual(result.limit, DEFAULT_GLOBAL_FOOD_LIMIT)

    def test_list_global_foods_caps_limit(self):
        result = list_global_foods(
            limit=999,
        )

        self.assertEqual(result.limit, MAX_GLOBAL_FOOD_LIMIT)

    def test_list_global_foods_resolves_source_from_metadata(self):
        result = list_global_foods(
            search="oats",
        )

        self.assertEqual(result.foods[0].source, FoodSourceMetadata.SOURCE_USDA)
