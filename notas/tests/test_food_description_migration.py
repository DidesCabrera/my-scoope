import importlib
from types import SimpleNamespace
from uuid import UUID

from django.apps import apps
from django.db import connection
from django.test import TestCase

from food_catalog.models import CatalogFood
from notas.domain.models import Food


class FoodDescriptionMigrationTests(TestCase):
    def test_reviewed_batch_matches_exact_global_identities_without_overwriting_edits(self):
        catalog = CatalogFood.objects.create(
            catalog_ref=UUID("b806c80e-0ea2-4b9f-aa41-4607fec28269"),
            display_name="Aceite de oliva",
            protein_g_per_100g=0,
            carbs_g_per_100g=0,
            fat_g_per_100g=100,
            status=CatalogFood.STATUS_PUBLISHED,
        )
        linked = Food.objects.create(
            name="Aceite de oliva", protein=0, carbs=0, fat=100,
            is_global=True, catalog_food_ref=catalog.catalog_ref,
        )
        personal = Food.objects.create(name="Aceite de oliva", protein=0, carbs=0, fat=100)
        legacy = Food.objects.create(
            pk=63, name="Alimento", protein=0, carbs=0, fat=0,
            is_global=True, is_verified=False,
        )
        mismatched = Food.objects.create(
            pk=64, name="Otro alimento", protein=0, carbs=0, fat=0,
            is_global=True, is_verified=False,
        )

        schema_editor = SimpleNamespace(connection=connection)
        catalog_migration = importlib.import_module("food_catalog.migrations.0022_catalogfood_description")
        operational_migration = importlib.import_module("notas.migrations.0101_food_description")
        catalog_migration.apply_reviewed_descriptions(apps, schema_editor)
        operational_migration.apply_reviewed_descriptions(apps, schema_editor)

        catalog.refresh_from_db()
        linked.refresh_from_db()
        personal.refresh_from_db()
        legacy.refresh_from_db()
        mismatched.refresh_from_db()
        self.assertIn("Aceite vegetal", catalog.description)
        self.assertEqual(linked.description, catalog.description)
        self.assertEqual(personal.description, "")
        self.assertIn("no identifica", legacy.description)
        self.assertEqual(mismatched.description, "")

        catalog.description = "Corrección editorial posterior"
        catalog.save(update_fields=["description"])
        catalog_migration.apply_reviewed_descriptions(apps, schema_editor)
        operational_migration.apply_reviewed_descriptions(apps, schema_editor)
        catalog.refresh_from_db()
        self.assertEqual(catalog.description, "Corrección editorial posterior")
