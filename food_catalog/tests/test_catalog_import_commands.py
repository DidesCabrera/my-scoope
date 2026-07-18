import json
import tempfile
from decimal import Decimal
from pathlib import Path

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from food_catalog.application.imports.usda.mapper import (
    USDA_NUTRIENT_CARBS,
    USDA_NUTRIENT_FAT,
    USDA_NUTRIENT_PROTEIN,
)
from food_catalog.infrastructure.imports.catalog_import import CATALOG_SOURCE_NAME_USDA
from food_catalog.models import CatalogFood, CatalogFoodSource, CatalogImportBatch


class CatalogUSDAImportCommandTests(TestCase):
    def test_import_catalog_usda_foods_json_creates_catalog_candidates_only(self):
        payloads = [
            {
                "fdcId": 3001,
                "description": "Lentils, cooked",
                "foodCategory": {"description": "Legumes and Legume Products"},
                "foodNutrients": [
                    {"nutrient": {"number": USDA_NUTRIENT_PROTEIN}, "amount": 9.02},
                    {"nutrient": {"number": USDA_NUTRIENT_CARBS}, "amount": 20.1},
                    {"nutrient": {"number": USDA_NUTRIENT_FAT}, "amount": 0.38},
                ],
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample_usda.json"
            path.write_text(json.dumps(payloads), encoding="utf-8")

            call_command(
                "dry_run_catalog_usda_foods_json",
                str(path),
                source_version="2026-04",
                source_dataset="foundation_foods",
                limit=1,
                reason="Validate USDA sample.",
            )
            dry_run = CatalogImportBatch.objects.get(is_dry_run=True)

            call_command(
                "import_catalog_usda_foods_json",
                str(path),
                source_version="2026-04",
                source_dataset="foundation_foods",
                notes="Catalog candidate import",
                limit=1,
                dry_run_batch_id=dry_run.pk,
                reason="Apply approved USDA sample.",
            )

        self.assertEqual(CatalogFood.objects.count(), 1)
        self.assertEqual(CatalogFoodSource.objects.count(), 1)
        self.assertEqual(CatalogImportBatch.objects.count(), 2)

        catalog_food = CatalogFood.objects.get(canonical_name="lentils cooked")
        source = CatalogFoodSource.objects.get(catalog_food=catalog_food)
        batch = CatalogImportBatch.objects.get(is_dry_run=False)

        self.assertEqual(catalog_food.status, CatalogFood.STATUS_EXTERNAL_CANDIDATE)
        self.assertEqual(catalog_food.source_type, CatalogFood.SOURCE_USDA)
        self.assertEqual(catalog_food.protein_g_per_100g, Decimal("9.020"))
        self.assertEqual(source.source_name, CATALOG_SOURCE_NAME_USDA)
        self.assertEqual(source.source_food_id, "3001")
        self.assertEqual(source.import_batch, batch)
        self.assertEqual(source.source_type, CatalogFood.SOURCE_USDA)
        self.assertIsNotNone(batch.dry_run_batch)
        self.assertEqual(batch.total_rows, 1)
        self.assertEqual(batch.imported_rows, 1)
        self.assertEqual(batch.skipped_rows, 0)
        self.assertEqual(batch.failed_rows, 0)
        self.assertEqual(batch.status, CatalogImportBatch.STATUS_COMPLETED)

        operational_food_model = apps.get_model("notas", "Food")
        self.assertEqual(operational_food_model.objects.count(), 0)

    def test_dry_run_catalog_usda_foods_json_does_not_write_rows(self):
        payloads = [
            {
                "fdcId": 3002,
                "description": "Beans, cooked",
                "foodNutrients": [
                    {"nutrient": {"number": USDA_NUTRIENT_PROTEIN}, "amount": 8.86},
                    {"nutrient": {"number": USDA_NUTRIENT_CARBS}, "amount": 23.7},
                    {"nutrient": {"number": USDA_NUTRIENT_FAT}, "amount": 0.54},
                ],
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dry_run_usda.json"
            path.write_text(json.dumps(payloads), encoding="utf-8")

            call_command(
                "dry_run_catalog_usda_foods_json",
                str(path),
                source_version="2026-04",
                source_dataset="foundation_foods",
                limit=1,
                reason="Validate USDA sample.",
            )

        self.assertEqual(CatalogFood.objects.count(), 0)
        self.assertEqual(CatalogFoodSource.objects.count(), 0)
        self.assertEqual(CatalogImportBatch.objects.filter(is_dry_run=True).count(), 1)
        self.assertEqual(CatalogImportBatch.objects.filter(is_dry_run=False).count(), 0)

    def test_import_catalog_usda_foods_json_skips_duplicates(self):
        payloads = [
            {
                "fdcId": 3003,
                "description": "Quinoa, cooked",
                "foodNutrients": [
                    {"nutrient": {"number": USDA_NUTRIENT_PROTEIN}, "amount": 4.4},
                    {"nutrient": {"number": USDA_NUTRIENT_CARBS}, "amount": 21.3},
                    {"nutrient": {"number": USDA_NUTRIENT_FAT}, "amount": 1.92},
                ],
            },
            {
                "fdcId": 3003,
                "description": "Quinoa, cooked duplicate",
                "foodNutrients": [
                    {"nutrient": {"number": USDA_NUTRIENT_PROTEIN}, "amount": 4.4},
                    {"nutrient": {"number": USDA_NUTRIENT_CARBS}, "amount": 21.3},
                    {"nutrient": {"number": USDA_NUTRIENT_FAT}, "amount": 1.92},
                ],
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dupes_usda.json"
            path.write_text(json.dumps(payloads), encoding="utf-8")

            call_command(
                "dry_run_catalog_usda_foods_json",
                str(path),
                source_version="2026-04",
                source_dataset="foundation_foods",
                limit=2,
                reason="Validate duplicate sample.",
            )
            dry_run = CatalogImportBatch.objects.get(is_dry_run=True)

            call_command(
                "import_catalog_usda_foods_json",
                str(path),
                source_version="2026-04",
                source_dataset="foundation_foods",
                limit=2,
                dry_run_batch_id=dry_run.pk,
                reason="Apply duplicate sample.",
            )

        batch = CatalogImportBatch.objects.get(is_dry_run=False)
        self.assertEqual(CatalogFood.objects.count(), 1)
        self.assertEqual(CatalogFoodSource.objects.count(), 1)
        self.assertEqual(batch.imported_rows, 1)
        self.assertEqual(batch.skipped_rows, 1)
        self.assertEqual(batch.failed_rows, 0)
        self.assertEqual(batch.summary_payload["reason_counts"]["duplicate_in_file"], 1)

    def test_import_catalog_usda_foods_json_rejects_missing_file(self):
        with self.assertRaises(CommandError):
            call_command(
                "import_catalog_usda_foods_json",
                "missing-file.json",
                source_version="2026-04",
                limit=1,
                dry_run_batch_id=1,
                reason="Apply.",
            )

    def test_usda_import_rejects_batch_over_global_maximum(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample_usda.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesMessage(CommandError, "between 1 and 500"):
                call_command(
                    "dry_run_catalog_usda_foods_json",
                    str(path),
                    source_version="2026-04",
                    limit=501,
                    reason="Invalid large sample.",
                )
