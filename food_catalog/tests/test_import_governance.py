from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from food_catalog.infrastructure.imports.governance import (
    CatalogImportGovernanceError,
    catalog_import_identity,
    record_catalog_import_dry_run,
    start_catalog_import_batch,
)
from food_catalog.models import CatalogFood, CatalogImportBatch


class CatalogImportGovernanceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="catalog-operator")
        self.identity = catalog_import_identity(
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="governed-source",
            source_version="2026-07-17",
            input_sha256="a" * 64,
            parameters_payload={"limit": 5},
        )

    def test_equivalent_completed_dry_run_authorizes_mutating_batch(self):
        dry_run = record_catalog_import_dry_run(
            identity=self.identity,
            total_rows=5,
            would_import_rows=4,
            skipped_rows=1,
            failed_rows=0,
            requested_by=self.user,
            reason="Validate a small sample.",
        )

        batch = start_catalog_import_batch(
            identity=self.identity,
            dry_run_batch=dry_run,
            total_rows=5,
            requested_by=self.user,
            reason="Apply approved sample.",
        )

        self.assertTrue(dry_run.is_dry_run)
        self.assertEqual(dry_run.status, CatalogImportBatch.STATUS_COMPLETED)
        self.assertFalse(batch.is_dry_run)
        self.assertEqual(batch.status, CatalogImportBatch.STATUS_RUNNING)
        self.assertEqual(batch.dry_run_batch, dry_run)
        self.assertEqual(batch.requested_by, self.user)
        self.assertEqual(batch.input_sha256, "a" * 64)
        self.assertEqual(batch.parameters_payload, {"limit": 5})

    def test_apply_rejects_non_dry_run_batch(self):
        not_a_dry_run = CatalogImportBatch.objects.create(
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="governed-source",
            source_version="2026-07-17",
            input_sha256="a" * 64,
            parameters_payload={"limit": 5},
            total_rows=5,
        )

        with self.assertRaisesMessage(CatalogImportGovernanceError, "not a dry-run"):
            start_catalog_import_batch(
                identity=self.identity,
                dry_run_batch=not_a_dry_run,
                total_rows=5,
                reason="Apply.",
            )

    def test_apply_rejects_changed_parameters(self):
        dry_run = record_catalog_import_dry_run(
            identity=self.identity,
            total_rows=5,
            would_import_rows=5,
            skipped_rows=0,
            failed_rows=0,
            reason="Validate.",
        )
        changed_identity = catalog_import_identity(
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="governed-source",
            source_version="2026-07-17",
            input_sha256="a" * 64,
            parameters_payload={"limit": 10},
        )

        with self.assertRaisesMessage(CatalogImportGovernanceError, "does not match"):
            start_catalog_import_batch(
                identity=changed_identity,
                dry_run_batch=dry_run,
                total_rows=5,
                reason="Apply.",
            )

    def test_apply_rejects_expired_dry_run(self):
        dry_run = record_catalog_import_dry_run(
            identity=self.identity,
            total_rows=5,
            would_import_rows=5,
            skipped_rows=0,
            failed_rows=0,
            reason="Validate.",
        )

        with self.assertRaisesMessage(CatalogImportGovernanceError, "expired"):
            start_catalog_import_batch(
                identity=self.identity,
                dry_run_batch=dry_run,
                total_rows=5,
                reason="Apply.",
                now=timezone.now() + timedelta(hours=25),
            )

    def test_reason_and_sha256_are_required(self):
        with self.assertRaisesMessage(CatalogImportGovernanceError, "SHA-256"):
            catalog_import_identity(
                source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
                source_name="governed-source",
                source_version="v1",
                input_sha256="short",
            )

    def test_open_food_facts_cannot_start_persistent_batch_without_license_approval(self):
        identity = catalog_import_identity(
            source_type=CatalogFood.SOURCE_OPEN_FOOD_FACTS,
            source_name="Open Food Facts",
            source_version="api-v3.6",
            input_sha256="b" * 64,
            parameters_payload={"limit": 3},
        )
        dry_run = record_catalog_import_dry_run(
            identity=identity,
            total_rows=3,
            would_import_rows=3,
            skipped_rows=0,
            failed_rows=0,
            reason="Evaluate OFF license gate.",
        )

        with self.assertRaisesMessage(CatalogImportGovernanceError, "persistence is disabled"):
            start_catalog_import_batch(
                identity=identity,
                dry_run_batch=dry_run,
                total_rows=3,
                reason="Attempt persistent OFF sample.",
            )
        self.assertEqual(CatalogImportBatch.objects.filter(is_dry_run=False).count(), 0)
        self.assertEqual(CatalogFood.objects.filter(source_type=CatalogFood.SOURCE_OPEN_FOOD_FACTS).count(), 0)

        with self.assertRaisesMessage(CatalogImportGovernanceError, "reason is required"):
            record_catalog_import_dry_run(
                identity=self.identity,
                total_rows=0,
                would_import_rows=0,
                skipped_rows=0,
                failed_rows=0,
                reason="",
            )
