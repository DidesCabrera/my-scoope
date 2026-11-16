"""Regression evidence for the seven food calorie-composition segments."""

import importlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase

from food_catalog.models import CatalogFood
from notas.domain.models import Food
from shared_kernel.food_macro_segments import (
    MACRO_SEGMENT_VERSION,
    classify_food_macro_segment,
)


class MacroSegmentTests(TestCase):
    def test_frozen_centers_reproduce_the_157_food_experiment(self):
        path = Path(__file__).resolve().parents[2] / "evaluation/foods_staging_2026-11-solver-v1.json"
        foods = json.loads(path.read_text(encoding="utf-8"))["foods"]
        counts = Counter(
            classify_food_macro_segment(food["protein"], food["carbs"], food["fat"])
            for food in foods
        )
        self.assertEqual(
            counts,
            Counter(A=67, B=36, C=15, D=12, E=9, F=12, G=6),
        )

    def test_catalog_and_operational_foods_keep_segment_in_sync_with_macros(self):
        catalog = CatalogFood.objects.create(
            display_name="Experimental food",
            protein_g_per_100g=Decimal("0"),
            carbs_g_per_100g=Decimal("100"),
            fat_g_per_100g=Decimal("0"),
        )
        food = Food.objects.create(name="Experimental food", protein=0, carbs=100, fat=0)
        self.assertEqual((catalog.macro_segment, food.macro_segment), ("A", "A"))

        catalog.carbs_g_per_100g = Decimal("0")
        catalog.fat_g_per_100g = Decimal("100")
        catalog.save(update_fields=["carbs_g_per_100g", "fat_g_per_100g"])
        food.carbs = 0
        food.fat = 100
        food.save(update_fields=["carbs", "fat"])
        catalog.refresh_from_db()
        food.refresh_from_db()
        self.assertEqual((catalog.macro_segment, food.macro_segment), ("G", "G"))
        self.assertEqual(catalog.macro_segment_version, MACRO_SEGMENT_VERSION)
        self.assertEqual(food.macro_segment_version, MACRO_SEGMENT_VERSION)

    def test_zero_or_invalid_macros_have_no_fabricated_segment(self):
        self.assertEqual(classify_food_macro_segment(0, 0, 0), "")
        self.assertEqual(classify_food_macro_segment(-1, 10, 0), "")
        self.assertEqual(classify_food_macro_segment(float("nan"), 10, 0), "")
        food = Food.objects.create(name="No energy", protein=0, carbs=0, fat=0)
        self.assertEqual(food.macro_segment, "")
        self.assertEqual(food.macro_segment_version, MACRO_SEGMENT_VERSION)

    def test_backfill_classifies_preexisting_rows_in_both_authorities(self):
        catalog = CatalogFood.objects.create(
            display_name="Preexisting catalog food",
            protein_g_per_100g=Decimal("0"),
            carbs_g_per_100g=Decimal("0"),
            fat_g_per_100g=Decimal("100"),
        )
        food = Food.objects.create(name="Preexisting operational food", protein=0, carbs=0, fat=100)
        CatalogFood.objects.filter(pk=catalog.pk).update(macro_segment="", macro_segment_version="")
        Food.objects.filter(pk=food.pk).update(macro_segment="", macro_segment_version="")

        editor = SimpleNamespace(connection=connection)
        catalog_migration = importlib.import_module(
            "food_catalog.migrations.0025_catalogfood_macro_segment_and_more"
        )
        food_migration = importlib.import_module(
            "notas.migrations.0105_food_macro_segment_food_macro_segment_version"
        )
        catalog_migration.backfill_catalog_macro_segments(apps, editor)
        food_migration.backfill_operational_macro_segments(apps, editor)

        catalog.refresh_from_db()
        food.refresh_from_db()
        self.assertEqual((catalog.macro_segment, food.macro_segment), ("G", "G"))
        self.assertEqual(catalog.macro_segment_version, MACRO_SEGMENT_VERSION)
        self.assertEqual(food.macro_segment_version, MACRO_SEGMENT_VERSION)
