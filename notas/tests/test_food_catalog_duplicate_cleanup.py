from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from food_catalog.models import CatalogFood
from notas.application.services.food_catalog_duplicate_cleanup import audit_food_catalog_duplicates
from notas.domain.models import Food


class FoodCatalogDuplicateCleanupTests(TransactionTestCase):
    def test_audit_apply_and_migration_retire_duplicates_without_deleting_food_ids(self):
        executor = MigrationExecutor(connection)
        executor.migrate([("notas", "0078_calendar_commitment_nutritionist")])
        try:
            first_catalog = self._catalog("Primer alimento")
            first = self._food(first_catalog)
            first_duplicate = self._food(first_catalog)

            preview = audit_food_catalog_duplicates()
            self.assertEqual(preview.retired_count, 0)
            self.assertEqual(preview.groups[0].survivor_id, first.pk)
            self.assertEqual(preview.groups[0].retired_ids, (first_duplicate.pk,))

            applied = audit_food_catalog_duplicates(apply=True)
            self.assertEqual(applied.retired_count, 1)
            first_duplicate.refresh_from_db()
            self.assertFalse(first_duplicate.is_active)
            self.assertIsNone(first_duplicate.catalog_food_id)
            self.assertIsNone(first_duplicate.catalog_food_ref)
            self.assertEqual(first_duplicate.protein, 10.0)

            second_catalog = self._catalog("Segundo alimento")
            second = self._food(second_catalog)
            second_duplicate = self._food(second_catalog)
            MigrationExecutor(connection).migrate([("notas", "0079_unique_global_catalog_snapshots")])

            second_duplicate.refresh_from_db()
            self.assertTrue(Food.objects.filter(pk=second.pk, catalog_food_id=second_catalog.pk).exists())
            self.assertTrue(Food.objects.filter(pk=second_duplicate.pk).exists())
            self.assertFalse(second_duplicate.is_active)
            self.assertIsNone(second_duplicate.catalog_food_id)
            self.assertEqual(audit_food_catalog_duplicates().groups, ())
        finally:
            MigrationExecutor(connection).migrate([("notas", "0079_unique_global_catalog_snapshots")])

    def _catalog(self, name):
        return CatalogFood.objects.create(
            display_name=name,
            canonical_name=name.lower(),
            protein_g_per_100g=Decimal("10.000"),
            carbs_g_per_100g=Decimal("20.000"),
            fat_g_per_100g=Decimal("3.000"),
            status=CatalogFood.STATUS_PUBLISHED,
        )

    def _food(self, catalog):
        return Food.objects.create(
            name=catalog.display_name,
            protein=10,
            carbs=20,
            fat=3,
            is_global=True,
            catalog_food_id=catalog.pk,
            catalog_food_ref=catalog.catalog_ref,
            catalog_sync_status=Food.CATALOG_SYNC_SNAPSHOT,
        )
