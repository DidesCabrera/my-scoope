import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from food_catalog.models import CatalogFood, CatalogFoodSource, CatalogImportBatch


class USDAManifestCommandTests(TestCase):
    def setUp(self):
        self.manifest_path = (
            Path(__file__).resolve().parents[1] / "data" / "generic_food_coverage_manifest_v1.csv"
        )
        payload = {
            "SRLegacyFoods": [
                {
                    "fdcId": 168421,
                    "dataType": "SR Legacy",
                    "description": "Kale, raw",
                    "foodCategory": {"description": "Vegetables and Vegetable Products"},
                    "foodNutrients": [
                        {"nutrient": {"number": "203"}, "amount": 2.92},
                        {"nutrient": {"number": "204"}, "amount": 1.49},
                        {"nutrient": {"number": "205"}, "amount": 4.42},
                        {"nutrient": {"number": "208"}, "amount": 35},
                    ],
                }
            ]
        }
        self.dataset = tempfile.NamedTemporaryFile(mode="w", suffix=".json", encoding="utf-8")
        json.dump(payload, self.dataset)
        self.dataset.flush()

    def tearDown(self):
        self.dataset.close()

    def test_governed_manifest_dry_run_and_apply_preserve_curated_semantics(self):
        common = [
            self.dataset.name,
            "--manifest-path", str(self.manifest_path),
            "--manifest-version", "gfc.v1",
            "--expected-source", "usda_sr_legacy",
            "--limit", "1",
            "--offset", "1",
        ]
        call_command("dry_run_catalog_usda_manifest", *common, reason="Validate official sample.")
        dry_run = CatalogImportBatch.objects.get(is_dry_run=True)
        self.assertEqual(CatalogFood.objects.count(), 0)

        call_command(
            "import_catalog_usda_manifest",
            *common,
            dry_run_batch_id=dry_run.pk,
            reason="Apply validated sample.",
        )

        food = CatalogFood.objects.get()
        source = CatalogFoodSource.objects.get()
        self.assertEqual(food.display_name, "Kale crudo")
        self.assertEqual(food.preparation_state, CatalogFood.PREPARATION_RAW)
        self.assertEqual(food.calories_kcal_per_100g, 35)
        self.assertEqual(source.source_food_id, "168421")
        self.assertEqual(source.evidence_payload["source_description"], "Kale, raw")
        self.assertEqual(source.import_batch.dry_run_batch_id, dry_run.pk)
