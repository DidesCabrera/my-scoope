"""Regression checks for the independent six-band calorie-density axis."""

import importlib
from decimal import Decimal
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase

from food_catalog.models import CatalogFood
from notas.domain.models import Food
from shared_kernel.food_caloric_density import (
    CALORIC_DENSITY_VERSION,
    calculate_caloric_density,
)


class FoodCaloricDensityTests(TestCase):
    def test_frozen_interval_edges_and_missing_energy(self):
        self.assertEqual(calculate_caloric_density(25.57, 0, 0, 0, "g")[:2], (Decimal("0.2557"), "D1"))
        for index, boundary in enumerate(("0.2558", "0.4865", "0.9477", "2.0540", "4.5314"), 2):
            self.assertEqual(
                calculate_caloric_density(Decimal(boundary) * 100, 0, 0, 0, "g")[1],
                f"D{index}",
            )
        self.assertEqual(calculate_caloric_density(None, 0, 0, 0, "g")[:3], (None, "", ""))
        self.assertEqual(calculate_caloric_density(None, -1, 0, 0, "g")[:3], (None, "", ""))

    def test_declared_energy_wins_and_liquid_is_marked_approximate(self):
        density = calculate_caloric_density(165, 31, 0, 3.6, "ml")
        self.assertEqual(density, (Decimal("1.6500"), "D4", "declared", True))
        self.assertEqual(
            calculate_caloric_density(None, 31, 0, 3.6, "g"),
            (Decimal("1.5640"), "D4", "macro_4_4_9", False),
        )

    def test_saved_models_recalculate_without_changing_food_group(self):
        catalog = CatalogFood.objects.create(
            display_name="Example", myscoope_group="poultry",
            protein_g_per_100g=Decimal("31"), carbs_g_per_100g=Decimal("0"),
            fat_g_per_100g=Decimal("3.6"), calories_kcal_per_100g=Decimal("165"),
        )
        food = Food.objects.create(name="Example", protein=31, carbs=0, fat=3.6)
        self.assertEqual((catalog.caloric_density_source, food.caloric_density_source), ("declared", "macro_4_4_9"))
        self.assertEqual(catalog.myscoope_group, "poultry")
        self.assertEqual(catalog.caloric_density_version, CALORIC_DENSITY_VERSION)
        food.declared_energy_kcal_per_100_unit = Decimal("165")
        food.save(update_fields=["declared_energy_kcal_per_100_unit"])
        food.refresh_from_db()
        self.assertEqual((food.caloric_density_kcal_per_unit, food.caloric_density_segment), (Decimal("1.6500"), "D4"))

    def test_backfill_uses_matching_catalog_snapshot_and_macro_fallback(self):
        catalog = CatalogFood.objects.create(
            display_name="Matching", protein_g_per_100g=Decimal("31"),
            carbs_g_per_100g=Decimal("0"), fat_g_per_100g=Decimal("3.6"),
            calories_kcal_per_100g=Decimal("165"),
        )
        matched = Food.objects.create(
            name="Matching", protein=31, carbs=0, fat=3.6,
            catalog_food_id=catalog.id, catalog_food_ref=catalog.catalog_ref,
            catalog_snapshot_version=catalog.catalog_version,
        )
        unmatched = Food.objects.create(name="Unmatched", protein=31, carbs=0, fat=3.6)
        Food.objects.filter(pk__in=[matched.pk, unmatched.pk]).update(
            caloric_density_kcal_per_unit=None, caloric_density_segment="",
            caloric_density_source="", caloric_density_version="",
        )
        migration = importlib.import_module("notas.migrations.0106_food_caloric_density_estimated_and_more")
        migration.backfill_operational_density(apps, SimpleNamespace(connection=connection))
        matched.refresh_from_db()
        unmatched.refresh_from_db()
        self.assertEqual((matched.declared_energy_kcal_per_100_unit, matched.caloric_density_source), (Decimal("165"), "declared"))
        self.assertEqual((unmatched.declared_energy_kcal_per_100_unit, unmatched.caloric_density_source), (None, "macro_4_4_9"))
