import json
from pathlib import Path

from django.test import TestCase

from notas.application.services.commands.import_usda_food_payloads import (
    import_usda_food_payloads,
)
from notas.application.services.food_imports.usda.mapper import (
    USDA_NUTRIENT_CARBS,
    USDA_NUTRIENT_FAT,
    USDA_NUTRIENT_FIBER,
    USDA_NUTRIENT_PROTEIN,
    USDA_NUTRIENT_SODIUM,
    USDA_NUTRIENT_SUGARS,
)
from notas.domain.models import Food, FoodImportBatch, FoodSourceMetadata


class USDAFoodPayloadImportCommandTests(TestCase):
    def test_import_usda_food_payloads_imports_multiple_foods(self):
        payloads = [
            {
                "fdcId": 1001,
                "description": "Oats, raw",
                "foodCategory": {
                    "description": "Cereal Grains and Pasta",
                },
                "foodNutrients": [
                    {
                        "nutrient": {"number": USDA_NUTRIENT_PROTEIN},
                        "amount": 16.9,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_CARBS},
                        "amount": 66.3,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_FAT},
                        "amount": 6.9,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_FIBER},
                        "amount": 10.6,
                    },
                ],
            },
            {
                "fdcId": 1002,
                "description": "Chicken breast, cooked",
                "foodCategory": {
                    "description": "Poultry Products",
                },
                "foodNutrients": [
                    {
                        "nutrient": {"number": USDA_NUTRIENT_PROTEIN},
                        "amount": 31,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_CARBS},
                        "amount": 0,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_FAT},
                        "amount": 3.6,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_SODIUM},
                        "amount": 74,
                    },
                ],
            },
        ]

        result = import_usda_food_payloads(
            payloads=payloads,
            source_version="2026-04",
            source_dataset="foundation_foods",
            notes="Controlled USDA fixture import",
        )

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.imported_rows, 2)
        self.assertEqual(result.skipped_rows, 0)
        self.assertEqual(result.failed_rows, 0)

        self.assertEqual(Food.objects.count(), 2)
        self.assertEqual(FoodSourceMetadata.objects.count(), 2)
        self.assertEqual(FoodImportBatch.objects.count(), 1)

        oats = Food.objects.get(canonical_name="oats raw")
        chicken = Food.objects.get(canonical_name="chicken breast cooked")

        self.assertTrue(oats.is_global)
        self.assertTrue(chicken.is_global)

        self.assertEqual(oats.category, "system")
        self.assertEqual(chicken.category, "system")

        self.assertEqual(oats.food_group, "cereal_grains_and_pasta")
        self.assertEqual(chicken.food_group, "poultry_products")

        batch = result.batch

        self.assertEqual(batch.source, FoodSourceMetadata.SOURCE_USDA)
        self.assertEqual(batch.source_version, "2026-04")
        self.assertEqual(batch.status, FoodImportBatch.STATUS_COMPLETED)
        self.assertEqual(batch.total_rows, 2)
        self.assertEqual(batch.imported_rows, 2)
        self.assertEqual(batch.skipped_rows, 0)
        self.assertEqual(batch.failed_rows, 0)

    def test_import_usda_food_payloads_skips_duplicates(self):
        payloads = [
            {
                "fdcId": 1001,
                "description": "Oats, raw",
                "foodNutrients": [
                    {
                        "nutrient": {"number": USDA_NUTRIENT_PROTEIN},
                        "amount": 16.9,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_CARBS},
                        "amount": 66.3,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_FAT},
                        "amount": 6.9,
                    },
                ],
            },
            {
                "fdcId": 1001,
                "description": "Oats, raw duplicate",
                "foodNutrients": [
                    {
                        "nutrient": {"number": USDA_NUTRIENT_PROTEIN},
                        "amount": 16.9,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_CARBS},
                        "amount": 66.3,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_FAT},
                        "amount": 6.9,
                    },
                ],
            },
        ]

        result = import_usda_food_payloads(
            payloads=payloads,
            source_version="2026-04",
            source_dataset="foundation_foods",
        )

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.imported_rows, 1)
        self.assertEqual(result.skipped_rows, 1)
        self.assertEqual(result.failed_rows, 0)

        self.assertEqual(Food.objects.count(), 1)
        self.assertEqual(FoodSourceMetadata.objects.count(), 1)
        self.assertEqual(result.batch.status, FoodImportBatch.STATUS_COMPLETED)

    def test_import_usda_food_payloads_skips_invalid_payloads(self):
        payloads = [
            {
                "fdcId": 1001,
                "description": "Invalid USDA food",
                "foodNutrients": [
                    {
                        "nutrient": {"number": USDA_NUTRIENT_PROTEIN},
                        "amount": 60,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_CARBS},
                        "amount": 60,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_FAT},
                        "amount": 10,
                    },
                ],
            }
        ]

        result = import_usda_food_payloads(
            payloads=payloads,
            source_version="2026-04",
            source_dataset="foundation_foods",
        )

        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.imported_rows, 0)
        self.assertEqual(result.skipped_rows, 1)
        self.assertEqual(result.failed_rows, 0)

        self.assertEqual(Food.objects.count(), 0)
        self.assertEqual(FoodSourceMetadata.objects.count(), 0)
        self.assertEqual(result.batch.status, FoodImportBatch.STATUS_COMPLETED)

    def test_import_usda_food_payloads_maps_metadata(self):
        payloads = [
            {
                "fdcId": 1003,
                "description": "Bananas, raw",
                "foodCategory": {
                    "description": "Fruits and Fruit Juices",
                },
                "foodNutrients": [
                    {
                        "nutrient": {"number": USDA_NUTRIENT_PROTEIN},
                        "amount": 1.09,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_CARBS},
                        "amount": 22.8,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_FAT},
                        "amount": 0.33,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_SUGARS},
                        "amount": 12.2,
                    },
                ],
            }
        ]

        result = import_usda_food_payloads(
            payloads=payloads,
            source_version="2026-04",
            source_dataset="foundation_foods",
            notes="Banana fixture",
        )

        self.assertEqual(result.imported_rows, 1)

        food = Food.objects.get(canonical_name="bananas raw")
        metadata = FoodSourceMetadata.objects.get(food=food)

        self.assertEqual(metadata.source, FoodSourceMetadata.SOURCE_USDA)
        self.assertEqual(metadata.source_food_id, "1003")
        self.assertEqual(metadata.source_dataset, "foundation_foods")
        self.assertEqual(metadata.source_version, "2026-04")
        self.assertEqual(metadata.license_name, "CC0")
        self.assertEqual(metadata.attribution, "USDA FoodData Central")


    def test_import_usda_food_payloads_from_fixture_file(self):
        fixture_path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "food_imports"
            / "usda"
            / "sample_foundation_foods.json"
        )

        with fixture_path.open("r", encoding="utf-8") as fixture_file:
            payloads = json.load(fixture_file)

        result = import_usda_food_payloads(
            payloads=payloads,
            source_version="2026-04",
            source_dataset="foundation_foods",
            notes="Fixture import",
        )

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.imported_rows, 2)
        self.assertEqual(result.skipped_rows, 0)
        self.assertEqual(result.failed_rows, 0)

        self.assertEqual(Food.objects.count(), 2)
        self.assertEqual(FoodSourceMetadata.objects.count(), 2)


    def test_import_usda_food_payloads_counts_mapping_failures_without_aborting_batch(self):
        payloads = [
            {
                "fdcId": 4001,
                "description": "Rice, white, cooked",
                "foodCategory": {
                    "description": "Cereal Grains and Pasta",
                },
                "foodNutrients": [
                    {
                        "nutrient": {"number": USDA_NUTRIENT_PROTEIN},
                        "amount": 2.69,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_CARBS},
                        "amount": 28.2,
                    },
                    {
                        "nutrient": {"number": USDA_NUTRIENT_FAT},
                        "amount": 0.28,
                    },
                ],
            },
            {
                "fdcId": 4002,
                "description": "Broken nutrient payload",
                "foodNutrients": [
                    "this item is not a nutrient object",
                ],
            },
        ]

        result = import_usda_food_payloads(
            payloads=payloads,
            source_version="2026-04",
            source_dataset="foundation_foods",
            notes="Mapping failure resilience test",
        )

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.imported_rows, 1)
        self.assertEqual(result.skipped_rows, 0)
        self.assertEqual(result.failed_rows, 1)
        self.assertEqual(result.mapping_failed_rows, 1)

        self.assertEqual(Food.objects.count(), 1)
        self.assertEqual(FoodSourceMetadata.objects.count(), 1)
        self.assertEqual(FoodImportBatch.objects.count(), 1)

        batch = FoodImportBatch.objects.get()

        self.assertEqual(batch.total_rows, 2)
        self.assertEqual(batch.imported_rows, 1)
        self.assertEqual(batch.skipped_rows, 0)
        self.assertEqual(batch.failed_rows, 1)
        self.assertEqual(batch.status, FoodImportBatch.STATUS_COMPLETED_WITH_ERRORS)