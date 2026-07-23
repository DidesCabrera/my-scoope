from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

from food_catalog.application.manual_intake import dry_run_manual_evidence_csv
from food_catalog.models import CatalogFood, CatalogFoodSource, CatalogImportBatch


class ManualEvidenceIntakeTests(TestCase):
    def write_csv(self, row: str) -> Path:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "manual.csv"
        path.write_text(
            "display_name,canonical_name,country,food_group,preparation_state,protein_g_per_100g,carbs_g_per_100g,fat_g_per_100g,default_portion_g,evidence_url,evidence_reference,license_name,attribution,source_version\n" + row,
            encoding="utf-8",
        )
        return path

    def test_evidence_fields_are_required(self):
        path = self.write_csv("Avena,Avena,CL,cereals,dry,13,68,7,40,,,CC0,Fuente curada,2026-07")
        plan = dry_run_manual_evidence_csv(path, limit=1)
        self.assertEqual(plan.invalid_rows, 1)
        self.assertTrue(any("evidence_url is required" in error for error in plan.errors))

    def test_governed_command_creates_manual_candidate_with_source_and_batch(self):
        path = self.write_csv(
            "Avena tradicional,Avena tradicional,CL,cereals,dry,13,68,7,40,https://example.test/evidence,EVID-001,CC0,Tabla autorizada,2026-07"
        )
        call_command(
            "import_catalog_manual_foods_csv",
            str(path),
            "--dry-run",
            limit=1,
            reason="Validate curated evidence.",
        )
        dry_run = CatalogImportBatch.objects.get(is_dry_run=True)
        self.assertEqual(CatalogFood.objects.count(), 0)

        call_command(
            "import_catalog_manual_foods_csv",
            str(path),
            limit=1,
            reason="Apply reviewed manual evidence.",
            dry_run_batch_id=dry_run.pk,
        )

        food = CatalogFood.objects.get()
        source = CatalogFoodSource.objects.get()
        apply_batch = CatalogImportBatch.objects.get(is_dry_run=False)
        self.assertEqual(food.status, CatalogFood.STATUS_MANUAL_CANDIDATE)
        self.assertEqual(source.import_batch, apply_batch)
        self.assertEqual(source.evidence_payload["reference"], "EVID-001")
        self.assertEqual(apply_batch.dry_run_batch, dry_run)
        self.assertFalse(CatalogFood.objects.filter(status=CatalogFood.STATUS_PUBLISHED).exists())

    def test_repeat_is_idempotent(self):
        path = self.write_csv(
            "Avena tradicional,Avena tradicional,CL,cereals,dry,13,68,7,40,https://example.test/evidence,EVID-001,CC0,Tabla autorizada,2026-07"
        )
        for reason in ("First", "Second"):
            call_command(
                "import_catalog_manual_foods_csv", str(path), "--dry-run", limit=1, reason=f"{reason} dry-run."
            )
            dry_run = CatalogImportBatch.objects.filter(is_dry_run=True).latest("id")
            call_command(
                "import_catalog_manual_foods_csv",
                str(path),
                limit=1,
                reason=f"{reason} apply.",
                dry_run_batch_id=dry_run.pk,
            )
        self.assertEqual(CatalogFood.objects.count(), 1)
        self.assertEqual(CatalogFoodSource.objects.count(), 1)
        self.assertEqual(CatalogImportBatch.objects.filter(is_dry_run=False).count(), 2)
