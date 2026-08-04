from decimal import Decimal

from django.test import TestCase

from notas.application.dto.imported_food_dto import ImportedFoodDTO
from notas.application.services.commands.import_food_batch import import_food_batch
from notas.domain.models import Food, FoodImportBatch, FoodSourceMetadata


class ImportFoodBatchTests(TestCase):
    def test_import_food_batch_imports_multiple_foods(self):
        foods = [
            ImportedFoodDTO(
                source=FoodSourceMetadata.SOURCE_USDA,
                source_food_id="1001",
                source_dataset="foundation_foods",
                source_version="test-version",
                name="Oats",
                canonical_name="oats",
                protein=Decimal("16.9"),
                carbs=Decimal("66.3"),
                fat=Decimal("6.9"),
            ),
            ImportedFoodDTO(
                source=FoodSourceMetadata.SOURCE_USDA,
                source_food_id="1002",
                source_dataset="foundation_foods",
                source_version="test-version",
                name="Chicken breast",
                canonical_name="chicken breast",
                protein=Decimal("31"),
                carbs=Decimal("0"),
                fat=Decimal("3.6"),
            ),
        ]

        result = import_food_batch(
            source=FoodSourceMetadata.SOURCE_USDA,
            source_version="test-version",
            foods=foods,
            notes="Test USDA batch",
        )

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.imported_rows, 2)
        self.assertEqual(result.skipped_rows, 0)
        self.assertEqual(result.failed_rows, 0)

        self.assertEqual(Food.objects.count(), 2)
        self.assertEqual(FoodSourceMetadata.objects.count(), 2)

        batch = result.batch
        self.assertEqual(batch.status, FoodImportBatch.STATUS_COMPLETED)
        self.assertEqual(batch.source, FoodSourceMetadata.SOURCE_USDA)
        self.assertEqual(batch.source_version, "test-version")
        self.assertEqual(batch.total_rows, 2)
        self.assertEqual(batch.imported_rows, 2)
        self.assertEqual(batch.skipped_rows, 0)
        self.assertEqual(batch.failed_rows, 0)
        self.assertIsNotNone(batch.finished_at)

    def test_import_food_batch_counts_duplicate_as_skipped(self):
        foods = [
            ImportedFoodDTO(
                source=FoodSourceMetadata.SOURCE_USDA,
                source_food_id="1001",
                source_dataset="foundation_foods",
                source_version="test-version",
                name="Oats",
                canonical_name="oats",
                protein=Decimal("16.9"),
                carbs=Decimal("66.3"),
                fat=Decimal("6.9"),
            ),
            ImportedFoodDTO(
                source=FoodSourceMetadata.SOURCE_USDA,
                source_food_id="1001",
                source_dataset="foundation_foods",
                source_version="test-version",
                name="Oats duplicated",
                canonical_name="oats duplicated",
                protein=Decimal("16.9"),
                carbs=Decimal("66.3"),
                fat=Decimal("6.9"),
            ),
        ]

        result = import_food_batch(
            source=FoodSourceMetadata.SOURCE_USDA,
            source_version="test-version",
            foods=foods,
        )

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.imported_rows, 1)
        self.assertEqual(result.skipped_rows, 1)
        self.assertEqual(result.failed_rows, 0)

        self.assertEqual(Food.objects.count(), 1)
        self.assertEqual(FoodSourceMetadata.objects.count(), 1)
        self.assertEqual(result.batch.status, FoodImportBatch.STATUS_COMPLETED)

    def test_import_food_batch_counts_invalid_rows_as_skipped(self):
        foods = [
            ImportedFoodDTO(
                source=FoodSourceMetadata.SOURCE_USDA,
                source_food_id="",
                source_dataset="foundation_foods",
                source_version="test-version",
                name="Invalid oats",
                canonical_name="invalid oats",
                protein=Decimal("16.9"),
                carbs=Decimal("66.3"),
                fat=Decimal("6.9"),
            ),
        ]

        result = import_food_batch(
            source=FoodSourceMetadata.SOURCE_USDA,
            source_version="test-version",
            foods=foods,
        )

        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.imported_rows, 0)
        self.assertEqual(result.skipped_rows, 1)
        self.assertEqual(result.failed_rows, 0)

        self.assertEqual(Food.objects.count(), 0)
        self.assertEqual(FoodSourceMetadata.objects.count(), 0)
        self.assertEqual(result.batch.status, FoodImportBatch.STATUS_COMPLETED)

    def test_import_food_batch_handles_empty_list(self):
        result = import_food_batch(
            source=FoodSourceMetadata.SOURCE_USDA,
            source_version="test-version",
            foods=[],
        )

        self.assertEqual(result.total_rows, 0)
        self.assertEqual(result.imported_rows, 0)
        self.assertEqual(result.skipped_rows, 0)
        self.assertEqual(result.failed_rows, 0)

        self.assertEqual(FoodImportBatch.objects.count(), 1)
        self.assertEqual(result.batch.status, FoodImportBatch.STATUS_COMPLETED)
        self.assertIsNotNone(result.batch.finished_at)