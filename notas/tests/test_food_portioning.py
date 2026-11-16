"""Approved serving-form labels survive backfills and catalog snapshots."""

import importlib
from decimal import Decimal
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase

from food_catalog.models import CatalogFood
from notas.application.queries.solver_food_candidates import build_solver_food_profile
from notas.application.services.food_catalog_snapshots import create_operational_food_snapshot_from_catalog
from notas.domain.models import Food
from shared_kernel.food_portioning import (
    APPROVED_PORTIONING_ASSIGNMENTS,
    PORTIONING_VERSION,
)


class FoodPortioningTests(TestCase):
    def test_unknown_mode_cannot_be_saved(self):
        with self.assertRaises(ValueError):
            Food.objects.create(
                name="Invalid mode", protein=1, carbs=1, fat=1,
                portioning_mode="unsupported",
            )
        with self.assertRaises(ValueError):
            CatalogFood.objects.create(
                display_name="Invalid mode", protein_g_per_100g=Decimal("1"),
                carbs_g_per_100g=Decimal("1"), fat_g_per_100g=Decimal("1"),
                portioning_mode="unsupported",
            )

    def test_assignment_set_covers_329_unique_foods_and_222_catalog_refs(self):
        self.assertEqual(len(APPROVED_PORTIONING_ASSIGNMENTS), 329)
        self.assertEqual(len({row[0] for row in APPROVED_PORTIONING_ASSIGNMENTS}), 329)
        self.assertEqual(sum(bool(row[3]) for row in APPROVED_PORTIONING_ASSIGNMENTS), 222)
        self.assertEqual(
            {mode: sum(row[4] == mode for row in APPROVED_PORTIONING_ASSIGNMENTS)
             for mode in ("by_weight", "by_unit", "fixed_pack")},
            {"by_weight": 264, "by_unit": 54, "fixed_pack": 11},
        )

    def test_backfill_requires_exact_operational_identity(self):
        matching = Food.objects.create(
            id=1, name="Dextrosa", protein=0, carbs=100, fat=0, is_global=True
        )
        reused_id = Food.objects.create(
            id=2, name="Different food", protein=0, carbs=100, fat=0, is_global=True
        )
        migration = importlib.import_module(
            "notas.migrations.0107_food_portioning_mode_food_portioning_mode_version"
        )
        migration.backfill_operational_portioning(apps, SimpleNamespace(connection=connection))
        matching.refresh_from_db()
        reused_id.refresh_from_db()
        self.assertEqual((matching.portioning_mode, matching.portioning_mode_version),
                         ("by_weight", PORTIONING_VERSION))
        self.assertEqual(reused_id.portioning_mode, "")

    def test_linked_backfill_uses_catalog_ref_across_different_operational_ids(self):
        catalog_ref = next(row[3] for row in APPROVED_PORTIONING_ASSIGNMENTS if row[3])
        food = Food.objects.create(
            id=9000, name="Avena tradicional", protein=10, carbs=60, fat=7,
            is_global=True, catalog_food_ref=catalog_ref,
        )
        migration = importlib.import_module(
            "notas.migrations.0107_food_portioning_mode_food_portioning_mode_version"
        )
        migration.backfill_operational_portioning(apps, SimpleNamespace(connection=connection))
        food.refresh_from_db()
        self.assertEqual(food.portioning_mode, "by_weight")

    def test_catalog_backfill_uses_stable_ref_and_snapshot_copies_mode(self):
        catalog_ref = next(row[3] for row in APPROVED_PORTIONING_ASSIGNMENTS if row[3])
        expected_mode = next(row[4] for row in APPROVED_PORTIONING_ASSIGNMENTS if row[3] == catalog_ref)
        catalog = CatalogFood.objects.create(
            catalog_ref=catalog_ref,
            display_name="Example serving form",
            protein_g_per_100g=Decimal("10"),
            carbs_g_per_100g=Decimal("20"),
            fat_g_per_100g=Decimal("3"),
            status=CatalogFood.STATUS_PUBLISHED,
        )
        migration = importlib.import_module("food_catalog.migrations.0027_catalogfood_portioning_mode_and_more")
        migration.backfill_catalog_portioning(apps, SimpleNamespace(connection=connection))
        catalog.refresh_from_db()
        self.assertEqual((catalog.portioning_mode, catalog.portioning_mode_version),
                         (expected_mode, PORTIONING_VERSION))

        food = create_operational_food_snapshot_from_catalog(catalog).food
        profile = build_solver_food_profile(food)
        self.assertEqual((food.portioning_mode, food.portioning_mode_version),
                         (expected_mode, PORTIONING_VERSION))
        self.assertEqual(profile.metadata["portioning_mode"], expected_mode)
        self.assertEqual(profile.metadata["portioning_mode_version"], PORTIONING_VERSION)
