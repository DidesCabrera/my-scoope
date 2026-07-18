from pathlib import Path
from unittest import TestCase

from food_catalog.application.coverage_manifest import (
    CoverageManifestError,
    parse_coverage_manifest_csv,
)


HEADER = (
    "target_key,preferred_name_es,category,subcategory,preparation_state,priority_tier,"
    "chile_relevance,expected_source,source_food_id,source_dataset,source_version,"
    "mapping_status,catalog_food_id,coverage_status,discovery_origin,decision_reason"
)


class CoverageManifestTests(TestCase):
    def test_packaged_v1_manifest_is_complete_and_valid(self):
        manifest = parse_coverage_manifest_csv(
            (
                Path(__file__).resolve().parents[1]
                / "data"
                / "generic_food_coverage_manifest_v1.csv"
            ).read_text(encoding="utf-8"),
            version="gfc.v1",
        )

        self.assertEqual(manifest.total_targets, 282)
        self.assertEqual(
            manifest.counts_by_category(),
            {
                "dairy": 29,
                "fruit": 53,
                "legume": 36,
                "meat_seafood": 77,
                "vegetable": 87,
            },
        )
        self.assertEqual(manifest.counts_by_status(), {"defined": 252, "source_mapped": 30})

    def test_parses_defined_targets_without_materializing_source_or_catalog_ids(self):
        manifest = parse_coverage_manifest_csv(
            HEADER
            + "\n"
            + "veg-brocoli-crudo,Brócoli crudo,vegetable,cruciferous,raw,A,essential,"
            "usda_foundation,,,,candidate,,defined,,",
            version="gfc.v1",
        )

        self.assertEqual(manifest.total_targets, 1)
        self.assertEqual(manifest.targets[0].preferred_name_es, "Brócoli crudo")
        self.assertEqual(manifest.targets[0].source_food_id, "")
        self.assertEqual(len(manifest.sha256), 64)

    def test_reports_category_tier_status_and_funnel_counts(self):
        manifest = parse_coverage_manifest_csv(
            HEADER
            + "\n"
            + "veg-brocoli-crudo,Brócoli crudo,vegetable,cruciferous,raw,A,essential,"
            "usda_foundation,747447,Foundation,2026-04,mapped,31,reviewed,,\n"
            + "fruit-manzana-cruda,Manzana cruda,fruit,pome,raw,A,essential,"
            "usda_foundation,,,,candidate,,defined,,",
            version="gfc.v1",
        )

        self.assertEqual(manifest.counts_by_category(), {"fruit": 1, "vegetable": 1})
        self.assertEqual(manifest.counts_by_tier(), {"A": 2})
        self.assertEqual(manifest.counts_by_status(), {"defined": 1, "reviewed": 1})
        self.assertEqual(
            manifest.funnel_counts(),
            {
                "defined": 2,
                "source_mapped": 1,
                "dry_run_valid": 1,
                "imported": 1,
                "reviewed": 1,
                "published": 0,
                "snapshotted": 0,
            },
        )

    def test_sha_is_stable_regardless_of_row_order(self):
        first_row = (
            "veg-brocoli-crudo,Brócoli crudo,vegetable,cruciferous,raw,A,essential,"
            "usda_foundation,,,,candidate,,defined,,"
        )
        second_row = (
            "fruit-manzana-cruda,Manzana cruda,fruit,pome,raw,A,essential,"
            "usda_foundation,,,,candidate,,defined,,"
        )

        first = parse_coverage_manifest_csv(HEADER + "\n" + first_row + "\n" + second_row, version="v1")
        second = parse_coverage_manifest_csv(HEADER + "\n" + second_row + "\n" + first_row, version="v1")

        self.assertEqual(first.sha256, second.sha256)

    def test_rejects_duplicate_target_keys(self):
        row = (
            "veg-brocoli-crudo,Brócoli crudo,vegetable,cruciferous,raw,A,essential,"
            "usda_foundation,,,,candidate,,defined,,"
        )

        with self.assertRaisesRegex(CoverageManifestError, "duplicate target_key"):
            parse_coverage_manifest_csv(HEADER + "\n" + row + "\n" + row, version="v1")

    def test_rejects_accent_insensitive_duplicate_concepts(self):
        first = (
            "fruit-limon-crudo,Limón crudo,fruit,citrus,raw,A,essential,"
            "usda_foundation,,,,candidate,,defined,,"
        )
        second = (
            "fruit-limon-duplicate,Limon crudo,fruit,citrus,raw,B,common,"
            "usda_sr_legacy,,,,candidate,,defined,,"
        )

        with self.assertRaisesRegex(CoverageManifestError, "duplicate concept"):
            parse_coverage_manifest_csv(HEADER + "\n" + first + "\n" + second, version="v1")

    def test_rejects_source_mapped_target_without_traceable_source(self):
        row = (
            "legume-lenteja-cocida,Lenteja cocida,legume,lentils,cooked,A,essential,"
            "usda_foundation,,,,mapped,,source_mapped,,"
        )

        with self.assertRaisesRegex(CoverageManifestError, "source_food_id is required"):
            parse_coverage_manifest_csv(HEADER + "\n" + row, version="v1")

    def test_rejects_imported_target_without_catalog_food_id(self):
        row = (
            "dairy-leche-entera,Leche entera,dairy,milk,ready_to_eat,A,essential,"
            "usda_sr_legacy,1077,SR Legacy,2018,mapped,,imported,,"
        )

        with self.assertRaisesRegex(CoverageManifestError, "catalog_food_id is required"):
            parse_coverage_manifest_csv(HEADER + "\n" + row, version="v1")

    def test_requires_discovery_origin_for_discovered_target(self):
        row = (
            "veg-digueñe-crudo,Digueñe crudo,vegetable,mushrooms,raw,discovery,useful,"
            "manual_evidence,,,,unmapped,,defined,,"
        )

        with self.assertRaisesRegex(CoverageManifestError, "discovery_origin is required"):
            parse_coverage_manifest_csv(HEADER + "\n" + row, version="v1")

    def test_requires_reason_for_deferred_or_excluded_target(self):
        row = (
            "fruit-example,Fruta por definir,fruit,tropical,unknown,C,specialized,"
            "unmapped,,,,blocked,,deferred,,"
        )

        with self.assertRaisesRegex(CoverageManifestError, "decision_reason is required"):
            parse_coverage_manifest_csv(HEADER + "\n" + row, version="v1")

    def test_rejects_missing_required_columns(self):
        with self.assertRaisesRegex(CoverageManifestError, "Missing manifest columns"):
            parse_coverage_manifest_csv("target_key,preferred_name_es\na,b", version="v1")
