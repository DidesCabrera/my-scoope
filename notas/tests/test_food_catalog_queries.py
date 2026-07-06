from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.queries.food_catalog_queries import (
    DEFAULT_FOOD_CATALOG_LIMIT,
    MAX_FOOD_CATALOG_LIMIT,
    list_food_catalog_for_planning,
)
from notas.domain.models import Food


class FoodCatalogQueryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            password="pass123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="pass123",
        )

        self.system_banana = Food.objects.create(
            name="Plátano",
            protein=1.1,
            carbs=23,
            fat=0.3,
            created_by=None,
        )

        self.chicken = Food.objects.create(
            name="Pechuga pollo",
            protein=31,
            carbs=0,
            fat=3.6,
            created_by=self.user,
        )

        self.rice = Food.objects.create(
            name="Arroz blanco",
            protein=2.7,
            carbs=28,
            fat=0.3,
            created_by=self.user,
        )

        self.private_other_food = Food.objects.create(
            name="Private Other Food",
            protein=100,
            carbs=100,
            fat=100,
            created_by=self.other_user,
        )
        self.global_other_food = Food.objects.create(
            name="Global Other Food",
            protein=20,
            carbs=10,
            fat=2,
            created_by=self.other_user,
            is_global=True,
        )

    def test_list_food_catalog_returns_readable_foods(self):
        catalog = list_food_catalog_for_planning(
            user=self.user,
        )

        data = catalog.as_dict()

        food_names = {
            food["name"]
            for food in data["foods"]
        }

        self.assertIn("Plátano", food_names)
        self.assertIn("Pechuga pollo", food_names)
        self.assertIn("Arroz blanco", food_names)
        self.assertNotIn("Private Other Food", food_names)
        self.assertIn("Global Other Food", food_names)

        self.assertEqual(data["count"], 4)
        self.assertEqual(data["limit"], DEFAULT_FOOD_CATALOG_LIMIT)
        self.assertIsNone(data["search"])

    def test_list_food_catalog_marks_sources(self):
        catalog = list_food_catalog_for_planning(
            user=self.user,
        )

        data = catalog.as_dict()

        sources_by_name = {
            food["name"]: food["source"]
            for food in data["foods"]
        }

        self.assertEqual(sources_by_name["Plátano"], "system")
        self.assertEqual(sources_by_name["Pechuga pollo"], "user")
        self.assertEqual(sources_by_name["Arroz blanco"], "user")
        self.assertEqual(sources_by_name["Global Other Food"], "system")

    def test_list_food_catalog_returns_macros_and_kcal_per_100g(self):
        catalog = list_food_catalog_for_planning(
            user=self.user,
            search="Pechuga",
        )

        data = catalog.as_dict()

        self.assertEqual(data["count"], 1)

        food = data["foods"][0]

        self.assertEqual(food["food_id"], self.chicken.id)
        self.assertEqual(food["name"], "Pechuga pollo")
        self.assertEqual(food["protein"], 31.0)
        self.assertEqual(food["carbs"], 0.0)
        self.assertEqual(food["fat"], 3.6)
        self.assertEqual(food["unit"], "g")

        expected_kcal = 31.0 * 4 + 0.0 * 4 + 3.6 * 9

        self.assertAlmostEqual(food["kcal_per_100g"], expected_kcal)

    def test_list_food_catalog_does_not_expose_catalog_snapshot_trace_fields(self):
        self.chicken.catalog_food_id = 12345
        self.chicken.catalog_food_ref = "11111111-1111-4111-8111-111111111111"
        self.chicken.catalog_snapshot_version = "v9"
        self.chicken.catalog_sync_status = Food.CATALOG_SYNC_SNAPSHOT
        self.chicken.catalog_snapshot_payload = {
            "source": "food_catalog",
            "catalog_food_id": 12345,
            "catalog_food_ref": "11111111-1111-4111-8111-111111111111",
        }
        self.chicken.save(
            update_fields=[
                "catalog_food_id",
                "catalog_food_ref",
                "catalog_snapshot_version",
                "catalog_sync_status",
                "catalog_snapshot_payload",
            ]
        )

        catalog = list_food_catalog_for_planning(
            user=self.user,
            search="Pechuga",
        )

        data = catalog.as_dict()
        food = data["foods"][0]

        self.assertEqual(food["food_id"], self.chicken.id)
        self.assertNotIn("catalog_food_id", food)
        self.assertNotIn("catalog_food_ref", food)
        self.assertNotIn("catalog_snapshot_version", food)
        self.assertNotIn("catalog_snapshot_payload", food)
        self.assertNotIn("catalog_sync_status", food)

    def test_list_food_catalog_filters_by_search(self):
        catalog = list_food_catalog_for_planning(
            user=self.user,
            search="arroz",
        )

        data = catalog.as_dict()

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["search"], "arroz")
        self.assertEqual(data["foods"][0]["name"], "Arroz blanco")

    def test_list_food_catalog_strips_empty_search(self):
        catalog = list_food_catalog_for_planning(
            user=self.user,
            search="   ",
        )

        data = catalog.as_dict()

        self.assertEqual(data["count"], 4)
        self.assertIsNone(data["search"])

    def test_list_food_catalog_respects_limit(self):
        catalog = list_food_catalog_for_planning(
            user=self.user,
            limit=2,
        )

        data = catalog.as_dict()

        self.assertEqual(data["count"], 2)
        self.assertEqual(data["limit"], 2)

    def test_list_food_catalog_normalizes_invalid_limit(self):
        catalog = list_food_catalog_for_planning(
            user=self.user,
            limit=0,
        )

        data = catalog.as_dict()

        self.assertEqual(data["limit"], DEFAULT_FOOD_CATALOG_LIMIT)

    def test_list_food_catalog_caps_limit(self):
        catalog = list_food_catalog_for_planning(
            user=self.user,
            limit=999,
        )

        data = catalog.as_dict()

        self.assertEqual(data["limit"], MAX_FOOD_CATALOG_LIMIT)
