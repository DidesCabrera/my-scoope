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
    dry_run_core_natural_foods_seed,
)
from food_catalog.models import (
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodPortion,
    CatalogFoodSource,
)


class CoreNaturalFoodsSeedTests(TestCase):
    def test_packaged_seed_is_valid_and_launch_sized(self):
        foods = load_core_natural_foods_seed()
        validation = validate_core_natural_foods_seed(foods)

        self.assertTrue(validation.is_valid, validation.errors)
        self.assertGreaterEqual(validation.foods_count, 25)

    def test_dry_run_reports_rows_to_create_without_writes(self):
        result = dry_run_core_natural_foods_seed()

        self.assertGreaterEqual(result.total_rows, 25)
        self.assertEqual(result.total_rows, result.to_create)
        self.assertEqual(result.to_update, 0)
        self.assertEqual(CatalogFood.objects.count(), 0)

    def test_apply_creates_verified_catalog_foods_with_sources_portions_and_aliases(self):
        result = apply_core_natural_foods_seed()

        self.assertGreaterEqual(result.created_rows, 25)
        self.assertEqual(result.updated_rows, 0)
        self.assertEqual(result.published_rows, 0)

        food = CatalogFood.objects.get(canonical_name="pechuga de pollo cocida")
        self.assertEqual(food.status, CatalogFood.STATUS_VERIFIED)
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

    def test_apply_is_idempotent_and_updates_existing_rows(self):
        first = apply_core_natural_foods_seed()
        second = apply_core_natural_foods_seed()

        self.assertGreaterEqual(first.created_rows, 25)
        self.assertEqual(second.created_rows, 0)
        self.assertEqual(second.updated_rows, first.total_rows)
        self.assertEqual(CatalogFood.objects.count(), first.total_rows)

    def test_apply_with_publish_uses_publication_workflow(self):
        result = apply_core_natural_foods_seed(publish=True)

        self.assertGreaterEqual(result.published_rows, 25)
        self.assertFalse(result.blocked_publications)
        self.assertEqual(
            CatalogFood.objects.filter(status=CatalogFood.STATUS_PUBLISHED).count(),
            result.total_rows,
        )

    def test_management_commands_run(self):
        call_command("dry_run_catalog_core_natural_foods")
        call_command("apply_catalog_core_natural_foods")

        self.assertGreaterEqual(CatalogFood.objects.count(), 25)
        self.assertEqual(CatalogFoodSource.objects.count(), CatalogFood.objects.count())
        self.assertGreater(CatalogFoodPortion.objects.count(), CatalogFood.objects.count())
        self.assertGreater(CatalogFoodAlias.objects.count(), CatalogFood.objects.count())
