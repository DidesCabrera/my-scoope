from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from food_catalog.models import CatalogFood
from notas.application.services.food_catalog_duplicate_cleanup import audit_food_catalog_duplicates
from notas.domain.models import Food, Meal, MealFood


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
            MigrationExecutor(connection).migrate([("notas", "0080_unique_active_global_food_names")])

    def test_name_migration_hides_legacy_public_duplicates_without_deleting_history(self):
        MigrationExecutor(connection).migrate([("notas", "0079_unique_global_catalog_snapshots")])
        try:
            catalog = self._catalog("Arroz blanco cocido")
            snapshot = self._food(catalog)
            legacy = Food.objects.create(
                name=" ARROZ BLANCO COCIDO ",
                protein=2.5,
                carbs=28.2,
                fat=0.2,
                is_global=True,
            )
            meal = Meal.objects.create(
                name="Comida histórica",
                created_by=User.objects.create_user(username="historic-meal-owner"),
            )
            meal_food = MealFood.objects.create(meal=meal, food=legacy, quantity=100)
            first_honey = Food.objects.create(
                name="Miel", protein=0, carbs=83, fat=0, is_global=True,
            )
            second_honey = Food.objects.create(
                name=" miel ", protein=0.3, carbs=82.4, fat=0, is_global=True,
            )
            self.assertEqual(
                audit_food_catalog_duplicates().possible_name_duplicates,
                (("arroz blanco cocido", 2), ("miel", 2)),
            )

            MigrationExecutor(connection).migrate([("notas", "0080_unique_active_global_food_names")])

            snapshot.refresh_from_db()
            legacy.refresh_from_db()
            first_honey.refresh_from_db()
            second_honey.refresh_from_db()
            self.assertTrue(snapshot.is_active)
            self.assertFalse(legacy.is_active)
            self.assertEqual(legacy.carbs, 28.2)
            self.assertTrue(Food.objects.filter(pk=legacy.pk).exists())
            meal_food.refresh_from_db()
            self.assertEqual(meal_food.food_id, legacy.pk)
            self.assertEqual(meal_food.carbs, 28.2)
            self.assertTrue(first_honey.is_active)
            self.assertFalse(second_honey.is_active)
            self.assertEqual(audit_food_catalog_duplicates().possible_name_duplicates, ())

            with self.assertRaises(IntegrityError), transaction.atomic():
                Food.objects.create(
                    name="  MIEL  ", protein=0, carbs=83, fat=0, is_global=True,
                )
            Food.objects.create(name="Miel", protein=0, carbs=83, fat=0, is_global=False)
            Food.objects.create(name="Miel", protein=0, carbs=83, fat=0, is_global=False)
        finally:
            MigrationExecutor(connection).migrate([("notas", "0080_unique_active_global_food_names")])

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
