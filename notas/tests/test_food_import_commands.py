from decimal import Decimal

from django.test import TestCase

from notas.application.dto.imported_food_dto import ImportedFoodDTO
from notas.application.services.commands.import_food_from_source import import_food_from_source
from notas.domain.models import Food, FoodSourceMetadata


class ImportFoodFromSourceTests(TestCase):
    def test_import_food_from_source_creates_global_food(self):
        dto = ImportedFoodDTO(
            source=FoodSourceMetadata.SOURCE_USDA,
            source_food_id="12345",
            source_dataset="foundation_foods",
            source_version="test-version",
            name="Oats",
            canonical_name="oats",
            protein=Decimal("16.9"),
            carbs=Decimal("66.3"),
            fat=Decimal("6.9"),
            food_group="cereals",
            food_subgroup="oats",
            fiber_g_per_100g=Decimal("10.6"),
            sugar_g_per_100g=Decimal("0.9"),
            license_name="CC0",
            attribution="USDA FoodData Central",
        )

        result = import_food_from_source(dto)

        self.assertTrue(result.created)
        self.assertFalse(result.skipped)

        food = result.food

        self.assertEqual(food.name, "Oats")
        self.assertEqual(food.canonical_name, "oats")
        self.assertEqual(food.protein, 16.9)
        self.assertEqual(food.carbs, 66.3)
        self.assertEqual(food.fat, 6.9)
        self.assertTrue(food.is_global)
        self.assertFalse(food.is_verified)
        self.assertTrue(food.is_active)
        self.assertEqual(food.category, "system")
        self.assertEqual(food.food_group, "cereals")
        self.assertEqual(food.food_subgroup, "oats")
        self.assertEqual(food.visibility, Food.VISIBILITY_EXTENDED)

    def test_import_food_from_source_creates_source_metadata(self):
        dto = ImportedFoodDTO(
            source=FoodSourceMetadata.SOURCE_USDA,
            source_food_id="12345",
            source_dataset="foundation_foods",
            source_version="test-version",
            name="Oats",
            canonical_name="oats",
            protein=Decimal("16.9"),
            carbs=Decimal("66.3"),
            fat=Decimal("6.9"),
            license_name="CC0",
            attribution="USDA FoodData Central",
        )

        result = import_food_from_source(dto)

        metadata = FoodSourceMetadata.objects.get(food=result.food)

        self.assertEqual(metadata.source, FoodSourceMetadata.SOURCE_USDA)
        self.assertEqual(metadata.source_food_id, "12345")
        self.assertEqual(metadata.source_dataset, "foundation_foods")
        self.assertEqual(metadata.source_version, "test-version")
        self.assertEqual(metadata.license_name, "CC0")
        self.assertEqual(metadata.attribution, "USDA FoodData Central")

    def test_import_food_from_source_does_not_duplicate_same_source_food_id(self):
        dto = ImportedFoodDTO(
            source=FoodSourceMetadata.SOURCE_USDA,
            source_food_id="12345",
            source_dataset="foundation_foods",
            source_version="test-version",
            name="Oats",
            canonical_name="oats",
            protein=Decimal("16.9"),
            carbs=Decimal("66.3"),
            fat=Decimal("6.9"),
        )

        first_result = import_food_from_source(dto)
        second_result = import_food_from_source(dto)

        self.assertTrue(first_result.created)
        self.assertFalse(first_result.skipped)

        self.assertFalse(second_result.created)
        self.assertTrue(second_result.skipped)
        self.assertEqual(second_result.reason, "already_imported")
        self.assertEqual(Food.objects.count(), 1)
        self.assertEqual(FoodSourceMetadata.objects.count(), 1)

    def test_import_food_from_source_rejects_missing_source_food_id(self):
        dto = ImportedFoodDTO(
            source=FoodSourceMetadata.SOURCE_USDA,
            source_food_id="",
            source_dataset="foundation_foods",
            source_version="test-version",
            name="Oats",
            canonical_name="oats",
            protein=Decimal("16.9"),
            carbs=Decimal("66.3"),
            fat=Decimal("6.9"),
        )

        result = import_food_from_source(dto)

        self.assertFalse(result.created)
        self.assertTrue(result.skipped)
        self.assertEqual(result.reason, "missing_source_food_id")
        self.assertEqual(Food.objects.count(), 0)

    def test_import_food_from_source_rejects_negative_macros(self):
        dto = ImportedFoodDTO(
            source=FoodSourceMetadata.SOURCE_USDA,
            source_food_id="12345",
            source_dataset="foundation_foods",
            source_version="test-version",
            name="Invalid food",
            canonical_name="invalid food",
            protein=Decimal("-1"),
            carbs=Decimal("10"),
            fat=Decimal("2"),
        )

        result = import_food_from_source(dto)

        self.assertFalse(result.created)
        self.assertTrue(result.skipped)
        self.assertEqual(result.reason, "invalid_negative_protein")
        self.assertEqual(Food.objects.count(), 0)

    def test_import_food_from_source_normalizes_before_creating_food(self):
        dto = ImportedFoodDTO(
            source=" USDA ",
            source_food_id=" 12345 ",
            source_dataset=" Foundation Foods ",
            source_version=" 2026-04 ",
            name="  Oats   Raw  ",
            canonical_name="  OATS   RAW ",
            protein=Decimal("16.9"),
            carbs=Decimal("66.3"),
            fat=Decimal("6.9"),
            food_group=" Cereals ",
            food_subgroup=" Oats ",
        )

        result = import_food_from_source(dto)

        self.assertTrue(result.created)
        self.assertEqual(result.food.name, "Oats Raw")
        self.assertEqual(result.food.canonical_name, "oats raw")
        self.assertEqual(result.food.food_group, "cereals")
        self.assertEqual(result.food.food_subgroup, "oats")

        metadata = FoodSourceMetadata.objects.get(food=result.food)

        self.assertEqual(metadata.source, FoodSourceMetadata.SOURCE_USDA)
        self.assertEqual(metadata.source_food_id, "12345")
        self.assertEqual(metadata.source_dataset, "foundation_foods")
        self.assertEqual(metadata.source_version, "2026-04")

    def test_import_food_from_source_sets_quality_score(self):
        dto = ImportedFoodDTO(
            source=FoodSourceMetadata.SOURCE_USDA,
            source_food_id="98765",
            source_dataset="foundation_foods",
            source_version="2026-04",
            name="Oats",
            canonical_name="oats",
            protein=Decimal("16.9"),
            carbs=Decimal("66.3"),
            fat=Decimal("6.9"),
            food_group="cereals",
            food_subgroup="oats",
            fiber_g_per_100g=Decimal("10.6"),
            sugar_g_per_100g=Decimal("0.9"),
            saturated_fat_g_per_100g=Decimal("1.2"),
            sodium_mg_per_100g=Decimal("2"),
        )

        result = import_food_from_source(dto)

        self.assertTrue(result.created)
        self.assertGreater(result.food.data_quality_score, 60)

    def test_import_food_from_source_rejects_invalid_total_macros(self):
        dto = ImportedFoodDTO(
            source=FoodSourceMetadata.SOURCE_USDA,
            source_food_id="invalid-001",
            source_dataset="foundation_foods",
            source_version="2026-04",
            name="Invalid food",
            canonical_name="invalid food",
            protein=Decimal("60"),
            carbs=Decimal("60"),
            fat=Decimal("10"),
        )

        result = import_food_from_source(dto)

        self.assertFalse(result.created)
        self.assertTrue(result.skipped)
        self.assertEqual(result.reason, "invalid_total_macros_over_limit")
        self.assertEqual(Food.objects.count(), 0)
        self.assertEqual(FoodSourceMetadata.objects.count(), 0)