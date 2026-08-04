from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
import json
from django.urls import reverse

from food_catalog.models import CatalogFood, CatalogImportBatch, CatalogImportSourcePolicy
from food_catalog.models import CatalogFoodSource
from admin_operations.models import AdminOperationAuditEvent


class FoodCatalogImportsOperationsTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(username="ops-imports", is_staff=True)

    def test_imports_page_requires_staff(self):
        response = self.client.get(reverse("admin_operations_food_catalog_imports"))
        self.assertEqual(response.status_code, 302)

    def test_imports_page_shows_governance_and_correlation(self):
        dry_run = CatalogImportBatch.objects.create(
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="Manual evidence",
            source_version="v1",
            status=CatalogImportBatch.STATUS_COMPLETED,
            is_dry_run=True,
            requested_by=self.staff,
            reason="Validate sample",
            input_sha256="a" * 64,
            total_rows=3,
            imported_rows=3,
        )
        CatalogImportBatch.objects.create(
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="Manual evidence",
            source_version="v1",
            status=CatalogImportBatch.STATUS_COMPLETED,
            dry_run_batch=dry_run,
            requested_by=self.staff,
            reason="Apply approved sample",
            input_sha256="a" * 64,
            total_rows=3,
            imported_rows=3,
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin_operations_food_catalog_imports"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Imports y dry-runs del Food Catalog")
        self.assertContains(response, "Dry-run antes de toda mutación")
        self.assertContains(response, "Manual evidence")
        self.assertContains(response, f"dry-run #{dry_run.pk}")
        self.assertContains(response, "Apply approved sample")
        self.assertContains(response, "input aaaaaaaaaaaa…")

    def test_filters_batches_by_source_and_status(self):
        CatalogImportBatch.objects.create(
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="Visible source",
            status=CatalogImportBatch.STATUS_COMPLETED,
        )
        CatalogImportBatch.objects.create(
            source_type=CatalogFood.SOURCE_BRAND_SUBMITTED,
            source_name="Hidden source",
            status=CatalogImportBatch.STATUS_FAILED,
        )
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("admin_operations_food_catalog_imports"),
            {"source": CatalogFood.SOURCE_ADMIN_IMPORT, "status": CatalogImportBatch.STATUS_COMPLETED},
        )

        self.assertContains(response, "Visible source")
        self.assertNotContains(response, "Hidden source")

    def test_core_seed_dry_run_then_apply_is_traced_and_does_not_publish(self):
        self.client.force_login(self.staff)
        dry_response = self.client.post(
            reverse("admin_operations_food_catalog_core_seed_dry_run"),
            {"reason": "Validate the packaged 30-food sample."},
        )
        self.assertEqual(dry_response.status_code, 302)
        dry_run = CatalogImportBatch.objects.get(is_dry_run=True)
        self.assertEqual(dry_run.total_rows, 30)
        self.assertEqual(CatalogFood.objects.count(), 0)

        apply_response = self.client.post(
            reverse("admin_operations_food_catalog_core_seed_apply"),
            {"dry_run_batch_id": dry_run.pk, "reason": "Apply approved seed sample."},
        )
        self.assertEqual(apply_response.status_code, 302)
        apply_batch = CatalogImportBatch.objects.get(is_dry_run=False)
        self.assertEqual(apply_batch.dry_run_batch, dry_run)
        self.assertEqual(CatalogFood.objects.count(), 30)
        self.assertEqual(
            CatalogFood.objects.filter(status=CatalogFood.STATUS_PENDING_REVIEW).count(),
            30,
        )
        self.assertEqual(CatalogFoodSource.objects.filter(import_batch=apply_batch).count(), 30)
        self.assertFalse(CatalogFood.objects.filter(status=CatalogFood.STATUS_PUBLISHED).exists())
        self.assertEqual(
            AdminOperationAuditEvent.objects.filter(
                action__in=["food_catalog.core_seed.dry_run", "food_catalog.core_seed.apply"]
            ).count(),
            2,
        )

    def test_core_seed_apply_without_equivalent_dry_run_is_rejected(self):
        self.client.force_login(self.staff)
        invalid = CatalogImportBatch.objects.create(
            source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
            source_name="Not a dry-run",
        )
        response = self.client.post(
            reverse("admin_operations_food_catalog_core_seed_apply"),
            {"dry_run_batch_id": invalid.pk, "reason": "Attempt apply."},
            follow=True,
        )
        self.assertContains(response, "No se pudo aplicar el seed")
        self.assertEqual(CatalogFood.objects.count(), 0)

    def test_usda_sample_dry_run_then_apply_uses_same_artifact(self):
        payload = json.dumps([{
            "fdcId": 991,
            "description": "Beans cooked sample",
            "foodNutrients": [
                {"nutrient": {"number": "203"}, "amount": 8.0},
                {"nutrient": {"number": "205"}, "amount": 22.0},
                {"nutrient": {"number": "204"}, "amount": 0.5},
            ],
        }]).encode()
        self.client.force_login(self.staff)
        common = {
            "source_version": "2026-04",
            "source_dataset": "foundation_foods",
            "limit": "1",
        }
        self.client.post(
            reverse("admin_operations_food_catalog_usda_dry_run"),
            {**common, "reason": "Validate USDA row.", "file": SimpleUploadedFile("usda.json", payload)},
        )
        dry_run = CatalogImportBatch.objects.get(is_dry_run=True)

        self.client.post(
            reverse("admin_operations_food_catalog_usda_apply"),
            {
                **common,
                "dry_run_batch_id": str(dry_run.pk),
                "reason": "Apply reviewed USDA row.",
                "file": SimpleUploadedFile("usda.json", payload),
            },
        )

        food = CatalogFood.objects.get()
        source = CatalogFoodSource.objects.get()
        apply_batch = CatalogImportBatch.objects.get(is_dry_run=False)
        self.assertEqual(food.source_type, CatalogFood.SOURCE_USDA)
        self.assertEqual(food.status, CatalogFood.STATUS_PENDING_REVIEW)
        self.assertEqual(source.source_type, CatalogFood.SOURCE_USDA)
        self.assertEqual(source.import_batch, apply_batch)
        self.assertEqual(apply_batch.dry_run_batch, dry_run)
        self.assertFalse(CatalogFood.objects.filter(status=CatalogFood.STATUS_PUBLISHED).exists())

    def test_scale_policy_approval_and_kill_switch_are_audited(self):
        self.client.force_login(self.staff)
        url = reverse("admin_operations_food_catalog_import_policy_action")
        common = {
            "source_type": CatalogFood.SOURCE_USDA,
            "source_name": "USDA governed scaling",
            "max_batch_rows": "100",
        }
        self.client.post(url, {**common, "action": "approve", "reason": "Two samples reviewed."})
        policy = CatalogImportSourcePolicy.objects.get()
        self.assertTrue(policy.scale_approved)
        self.assertFalse(policy.kill_switch)
        self.assertEqual(policy.max_batch_rows, 100)

        self.client.post(url, {**common, "action": "kill", "reason": "Unexpected source quality."})
        policy.refresh_from_db()
        self.assertTrue(policy.kill_switch)
        self.assertEqual(
            AdminOperationAuditEvent.objects.filter(action__startswith="food_catalog.import_policy.").count(),
            2,
        )
