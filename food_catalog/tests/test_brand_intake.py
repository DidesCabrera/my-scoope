from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import CommandError, call_command
from django.test import TestCase

from food_catalog.application.brand_intake import (
    apply_brand_food_intake_csv,
    brand_food_intake_identity,
    dry_run_brand_food_intake_csv,
    load_brand_food_intake_csv,
)
from food_catalog.infrastructure.imports.governance import record_catalog_import_dry_run
from food_catalog.models import (
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodPortion,
    CatalogFoodSource,
    CatalogImportBatch,
)


class BrandFoodIntakeTests(TestCase):
    def write_csv(self, content: str) -> Path:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "brand_foods.csv"
        path.write_text(content, encoding="utf-8")
        return path

    def valid_csv(self) -> str:
        return "\n".join(
            [
                "display_name,brand_name,canonical_name,barcode,country,food_group,food_subgroup,preparation_state,protein_g_per_100g,carbs_g_per_100g,fat_g_per_100g,calories_kcal_per_100g,default_portion_g,serving_label,solver_min_portion_g,solver_max_portion_g,solver_portion_step_g,aliases,label_evidence_url,authorization_reference,source_url,contact_email,authorization_confirmed,notes",
                "Yogur Griego Natural,Marca Uno,yogur griego natural marca uno,7800000000001,CL,lacteos,yogur,ready_to_eat,10.0,4.0,0.2,58,170,1 envase,100,250,10,yogur griego|greek yogurt,https://example.test/label,AUTH-1,https://example.test/producto,nutrition@example.test,yes,Autorizado por marca",
            ]
        )

    def test_load_valid_brand_intake_csv(self):
        path = self.write_csv(self.valid_csv())

        validations = load_brand_food_intake_csv(path)

        self.assertEqual(len(validations), 1)
        self.assertTrue(validations[0].is_valid, validations[0].errors)
        row = validations[0].row
        self.assertIsNotNone(row)
        self.assertEqual(row.brand_name, "Marca Uno")
        self.assertEqual(row.preparation_state, CatalogFood.PREPARATION_READY_TO_EAT)
        self.assertEqual(row.protein_g_per_100g, Decimal("10.0"))
        self.assertEqual(row.default_portion_g, Decimal("170"))
        self.assertTrue(row.authorization_confirmed)

    def test_invalid_without_authorization_is_rejected(self):
        path = self.write_csv(
            self.valid_csv().replace(",yes,Autorizado por marca", ",no,Autorizado por marca")
        )

        result = dry_run_brand_food_intake_csv(path)

        self.assertEqual(result.created_rows, 0)
        self.assertEqual(result.updated_rows, 0)
        self.assertEqual(result.skipped_rows, 1)
        self.assertIn("authorization_confirmed must be true/yes/sí/1", result.errors[0])
        self.assertEqual(CatalogFood.objects.count(), 0)

    def test_apply_creates_brand_submitted_catalog_food_with_source_portion_and_aliases(self):
        path = self.write_csv(self.valid_csv())

        result = apply_brand_food_intake_csv(
            path, dry_run_batch=self.record_dry_run(path), reason="Apply brand sample.", limit=1
        )

        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.created_rows, 1)
        self.assertEqual(result.updated_rows, 0)
        self.assertFalse(result.errors)

        food = CatalogFood.objects.get(canonical_name="yogur griego natural marca uno")
        self.assertEqual(food.status, CatalogFood.STATUS_BRAND_SUBMITTED)
        self.assertEqual(food.source_type, CatalogFood.SOURCE_BRAND_SUBMITTED)
        self.assertTrue(food.is_branded)
        self.assertEqual(food.brand_name, "Marca Uno")
        self.assertEqual(food.country, "CL")
        self.assertTrue(food.solver_enabled)
        self.assertEqual(food.solver_min_portion_g, Decimal("100"))
        self.assertEqual(food.solver_max_portion_g, Decimal("250"))
        self.assertEqual(food.solver_portion_step_g, Decimal("10"))

        portion = CatalogFoodPortion.objects.get(catalog_food=food, is_default=True)
        self.assertEqual(portion.label, "1 envase")
        self.assertEqual(portion.grams, Decimal("170"))

        source = CatalogFoodSource.objects.get(catalog_food=food)
        self.assertEqual(source.source_type, CatalogFood.SOURCE_BRAND_SUBMITTED)
        self.assertEqual(source.source_food_id, "7800000000001")
        self.assertEqual(source.license_status, CatalogFoodSource.LICENSE_ALLOWED)
        self.assertTrue(source.evidence_payload["authorization_confirmed"])
        self.assertEqual(source.evidence_payload["authorization_reference"], "AUTH-1")
        self.assertEqual(source.evidence_payload["contact_email"], "nutrition@example.test")

        self.assertTrue(CatalogFoodAlias.objects.filter(catalog_food=food, normalized_name="yogur griego").exists())
        self.assertTrue(CatalogFoodAlias.objects.filter(catalog_food=food, normalized_name="greek yogurt").exists())

    def test_apply_is_idempotent_and_updates_existing_brand_food(self):
        path = self.write_csv(self.valid_csv())
        first = apply_brand_food_intake_csv(
            path, dry_run_batch=self.record_dry_run(path), reason="First brand apply.", limit=1
        )
        second = apply_brand_food_intake_csv(
            path, dry_run_batch=self.record_dry_run(path), reason="Repeat brand apply.", limit=1
        )

        self.assertEqual(first.created_rows, 1)
        self.assertEqual(second.created_rows, 0)
        self.assertEqual(second.updated_rows, 1)
        self.assertEqual(CatalogFood.objects.count(), 1)
        self.assertEqual(CatalogFoodSource.objects.count(), 1)
        self.assertEqual(CatalogImportBatch.objects.count(), 4)

    def test_management_command_dry_run_does_not_write(self):
        path = self.write_csv(self.valid_csv())

        call_command(
            "import_catalog_brand_foods_csv", str(path), "--dry-run", limit=1, reason="Validate brand sample."
        )

        self.assertEqual(CatalogFood.objects.count(), 0)

    def test_management_command_imports_valid_csv(self):
        path = self.write_csv(self.valid_csv())

        call_command(
            "import_catalog_brand_foods_csv", str(path), "--dry-run", limit=1, reason="Validate brand sample."
        )
        dry_run = CatalogImportBatch.objects.get(is_dry_run=True)
        call_command(
            "import_catalog_brand_foods_csv",
            str(path),
            limit=1,
            reason="Apply brand sample.",
            dry_run_batch_id=dry_run.pk,
        )

        self.assertEqual(CatalogFood.objects.count(), 1)
        self.assertEqual(CatalogFood.objects.get().status, CatalogFood.STATUS_BRAND_SUBMITTED)

    def test_management_command_fails_invalid_csv_without_writes(self):
        path = self.write_csv(
            self.valid_csv().replace(",yes,Autorizado por marca", ",no,Autorizado por marca")
        )

        with self.assertRaises(CommandError):
                call_command(
                    "import_catalog_brand_foods_csv",
                    str(path),
                    "--dry-run",
                    limit=1,
                    reason="Validate invalid brand sample.",
                )

        self.assertEqual(CatalogFood.objects.count(), 0)

    def test_missing_label_or_authorization_evidence_is_rejected(self):
        path = self.write_csv(self.valid_csv().replace("https://example.test/label,AUTH-1", ","))
        result = dry_run_brand_food_intake_csv(path)
        self.assertTrue(any("label_evidence_url is required" in error for error in result.errors))
        self.assertTrue(any("authorization_reference is required" in error for error in result.errors))

    def record_dry_run(self, path: Path):
        result = dry_run_brand_food_intake_csv(path, limit=1)
        return record_catalog_import_dry_run(
            identity=brand_food_intake_identity(path, limit=1),
            total_rows=result.total_rows,
            would_import_rows=result.total_rows - result.skipped_rows,
            skipped_rows=result.skipped_rows,
            failed_rows=0,
            reason="Validate brand sample.",
        )
