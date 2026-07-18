from pathlib import Path

from django.test import SimpleTestCase

from food_catalog.application.coverage_manifest import load_coverage_manifest
from food_catalog.application.imports.usda.manifest_selection import (
    USDAManifestSelectionError,
    select_usda_manifest_foods,
)


class USDAManifestSelectionTests(SimpleTestCase):
    def setUp(self):
        self.manifest = load_coverage_manifest(
            Path(__file__).resolve().parents[1] / "data" / "generic_food_coverage_manifest_v1.csv",
            version="gfc.v1",
        )

    def test_selects_mapped_rows_by_fdc_id_and_applies_curated_semantics(self):
        payload = {
            "fdcId": 168421,
            "dataType": "SR Legacy",
            "description": "Kale, raw",
            "foodCategory": {"description": "Vegetables and Vegetable Products"},
            "foodNutrients": [],
        }

        result = select_usda_manifest_foods(
            manifest=self.manifest,
            payloads=[payload],
            expected_source="usda_sr_legacy",
            offset=6,
            limit=1,
        )

        self.assertEqual(result.targets[0].target_key, "vegetable-kale-crudo")
        self.assertEqual(result.foods[0].name, "Kale crudo")
        self.assertEqual(result.foods[0].source_description, "Kale, raw")
        self.assertEqual(result.foods[0].preparation_state, "raw")

    def test_rejects_a_manifest_mapping_absent_from_supplied_dataset(self):
        with self.assertRaisesRegex(USDAManifestSelectionError, "168421"):
            select_usda_manifest_foods(
                manifest=self.manifest,
                payloads=[],
                expected_source="usda_sr_legacy",
                offset=6,
                limit=1,
            )
