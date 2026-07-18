from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from food_catalog.models import CatalogFood, CatalogImportBatch


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
