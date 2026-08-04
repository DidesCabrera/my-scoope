from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from food_catalog.application.core_natural_foods import (
    CORE_NATURAL_FOODS_SOURCE_NAME,
    load_core_natural_foods_seed,
    validate_core_natural_foods_seed,
)
from food_catalog.infrastructure.core_natural_foods_seed import (
    apply_core_natural_foods_seed,
    core_natural_foods_seed_identity,
    dry_run_core_natural_foods_seed,
)
from food_catalog.infrastructure.imports.governance import (
    CatalogImportGovernanceError,
    record_catalog_import_dry_run,
)
from food_catalog.models import (
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodPortion,
    CatalogFoodSource,
    CatalogImportBatch,
)


class CoreNaturalFoodsSeedTests(TestCase):
    def test_packaged_seed_is_valid_and_launch_sized(self):
        foods = load_core_natural_foods_seed()
        validation = validate_core_natural_foods_seed(foods)

        self.assertTrue(validation.is_valid, validation.errors)
        self.assertEqual(validation.foods_count, 30)

    def test_dry_run_reports_rows_to_create_without_writes(self):
        result = dry_run_core_natural_foods_seed()

        self.assertEqual(result.total_rows, 30)
        self.assertEqual(result.total_rows, result.to_create)
        self.assertEqual(result.to_update, 0)
        self.assertEqual(CatalogFood.objects.count(), 0)

    def test_apply_creates_verified_catalog_foods_with_sources_portions_and_aliases(self):
        dry_run = self.record_dry_run()
        result = apply_core_natural_foods_seed(dry_run_batch=dry_run, reason="Apply seed sample.")

        self.assertEqual(result.created_rows, 30)
        self.assertEqual(result.updated_rows, 0)
        self.assertEqual(result.batch.dry_run_batch, dry_run)

        food = CatalogFood.objects.get(canonical_name="pechuga de pollo cocida")
        self.assertEqual(food.status, CatalogFood.STATUS_PENDING_REVIEW)
        self.assertEqual(food.source_type, CatalogFood.SOURCE_NATURAL_VERIFIED)
        self.assertEqual(food.country, "CL")
        self.assertEqual(food.preparation_state, CatalogFood.PREPARATION_COOKED)
        self.assertTrue(food.solver_enabled)
        self.assertEqual(food.protein_g_per_100g, Decimal("31.020"))
        self.assertTrue(food.portions.filter(is_default=True).exists())
        self.assertTrue(food.aliases.filter(normalized_name="chicken breast cooked").exists())

        source = CatalogFoodSource.objects.get(catalog_food=food)
        self.assertEqual(source.source_name, CORE_NATURAL_FOODS_SOURCE_NAME)
        self.assertEqual(source.license_status, CatalogFoodSource.LICENSE_ALLOWED)
        self.assertEqual(source.import_batch, result.batch)

    def test_apply_is_idempotent_and_updates_existing_rows(self):
        first = apply_core_natural_foods_seed(dry_run_batch=self.record_dry_run(), reason="First apply.")
        second = apply_core_natural_foods_seed(dry_run_batch=self.record_dry_run(), reason="Idempotency apply.")

        self.assertEqual(first.created_rows, 30)
        self.assertEqual(second.created_rows, 0)
        self.assertEqual(second.updated_rows, first.total_rows)
        self.assertEqual(CatalogFood.objects.count(), first.total_rows)

    def test_apply_never_publishes_and_rejects_non_dry_run(self):
        invalid_batch = CatalogImportBatch.objects.create(
            source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
            source_name=CORE_NATURAL_FOODS_SOURCE_NAME,
        )
        with self.assertRaises(CatalogImportGovernanceError):
            apply_core_natural_foods_seed(dry_run_batch=invalid_batch, reason="Invalid apply.")
        self.assertEqual(CatalogFood.objects.filter(status=CatalogFood.STATUS_PUBLISHED).count(), 0)

    def test_management_commands_run(self):
        call_command("dry_run_catalog_core_natural_foods", reason="Validate packaged seed.")
        dry_run = CatalogImportBatch.objects.get(is_dry_run=True)
        call_command(
            "apply_catalog_core_natural_foods",
            dry_run_batch_id=dry_run.pk,
            reason="Apply validated packaged seed.",
        )

        self.assertEqual(CatalogFood.objects.count(), 30)
        self.assertEqual(CatalogFoodSource.objects.count(), CatalogFood.objects.count())
        self.assertGreater(CatalogFoodPortion.objects.count(), CatalogFood.objects.count())
        self.assertGreater(CatalogFoodAlias.objects.count(), CatalogFood.objects.count())
        self.assertFalse(CatalogFood.objects.filter(status=CatalogFood.STATUS_PUBLISHED).exists())

    def record_dry_run(self):
        plan = dry_run_core_natural_foods_seed()
        return record_catalog_import_dry_run(
            identity=core_natural_foods_seed_identity(),
            total_rows=plan.total_rows,
            would_import_rows=plan.to_create + plan.to_update,
            skipped_rows=plan.invalid_rows,
            failed_rows=0,
            reason="Validate seed.",
        )
