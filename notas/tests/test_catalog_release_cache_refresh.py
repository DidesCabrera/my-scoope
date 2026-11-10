import json
import tempfile
from datetime import date, time
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from food_catalog.infrastructure.releases import (
    approve_catalog_release,
    build_catalog_release,
    import_catalog_release,
    release_envelope,
)
from food_catalog.models import CatalogFood, CatalogFoodPortion, CatalogFoodSource, CatalogRelease
from notas.application.services.cache.dailyplan_summary import refresh_dailyplan_and_related_program_caches
from notas.application.services.calendarization.snapshots import build_dailyplan_snapshot_from_dailyplan
from notas.domain.models import CalendarizedDay, DailyPlanMeal, Food, Program, ProgramDay
from notas.tests.builders import attach_food, create_dailyplan, create_meal


class CatalogReleaseCacheRefreshTests(TestCase):
    def test_new_release_refreshes_live_caches_without_rewriting_calendar_snapshot(self):
        authority_food = _published_food()
        first_release = approve_catalog_release(build_catalog_release(version="2026.09.3"))
        first_envelope = release_envelope(first_release)
        CatalogRelease.objects.all().delete()
        CatalogFood.objects.all().delete()

        import_catalog_release(first_envelope)
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "release-v1.json"
            first_path.write_text(json.dumps(first_envelope), encoding="utf-8")
            call_command("import_food_catalog_release", file=str(first_path), materialize=True)

            mirrored = CatalogFood.objects.get(catalog_ref=authority_food.catalog_ref)
            operational = Food.objects.get(catalog_food_id=mirrored.pk)
            operational_id = operational.pk
            self.assertEqual(operational.protein, Decimal("31.000"))

            owner = get_user_model().objects.create_user(username="catalog-release-owner")
            meal = create_meal(created_by=owner, name="Comida con alimento del catálogo")
            attach_food(meal=meal, food=operational, quantity=100)
            dailyplan = create_dailyplan(created_by=owner, name="Minuta con alimento del catálogo")
            DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=meal, hour=time(12, 0))
            program = Program.objects.create(name="Programa con alimento del catálogo", created_by=owner)
            ProgramDay.objects.create(program=program, dailyplan=dailyplan, week_number=1, day_number=1)
            refresh_dailyplan_and_related_program_caches(dailyplan)
            historical = build_dailyplan_snapshot_from_dailyplan(dailyplan)
            calendarized = CalendarizedDay.objects.create(
                user=owner,
                calendar_date=date(2026, 11, 12),
                source_kind=CalendarizedDay.SOURCE_MANUAL,
                source_dailyplan_id=dailyplan.pk,
                plan_snapshot=historical.payload,
                snapshot_hash=historical.content_hash,
            )
            self.assertEqual(meal.protein_cached, 31)

            mirrored.catalog_version = "v2"
            mirrored.protein_g_per_100g = Decimal("32.500")
            mirrored.is_release_managed = False
            mirrored.save(update_fields=["catalog_version", "protein_g_per_100g", "is_release_managed"])
            CatalogRelease.objects.all().delete()
            second_release = approve_catalog_release(build_catalog_release(version="2026.09.4"))
            second_envelope = release_envelope(second_release)
            CatalogRelease.objects.all().delete()
            second_path = Path(directory) / "release-v2.json"
            second_path.write_text(json.dumps(second_envelope), encoding="utf-8")
            call_command("import_food_catalog_release", file=str(second_path), materialize=True)

        operational.refresh_from_db()
        meal.refresh_from_db()
        dailyplan.refresh_from_db()
        program.refresh_from_db()
        calendarized.refresh_from_db()
        self.assertEqual(operational.pk, operational_id)
        self.assertEqual(operational.protein, Decimal("32.500"))
        self.assertEqual(operational.catalog_snapshot_version, "v2")
        self.assertEqual(meal.protein_cached, 32.5)
        self.assertEqual(dailyplan.summary_cache["totals"]["protein"], 32.5)
        self.assertEqual(program.summary_cache["program_totals"]["protein"], 32.5)
        self.assertEqual(calendarized.plan_snapshot, historical.payload)
        self.assertEqual(calendarized.snapshot_hash, historical.content_hash)


def _published_food() -> CatalogFood:
    food = CatalogFood.objects.create(
        display_name="Pechuga de pollo cocida",
        canonical_name="pechuga pollo cocida",
        catalog_version="v1",
        food_group="meats",
        food_subgroup="poultry",
        myscoope_group="poultry",
        preparation_state=CatalogFood.PREPARATION_COOKED,
        protein_g_per_100g=Decimal("31.000"),
        carbs_g_per_100g=Decimal("0.000"),
        fat_g_per_100g=Decimal("3.600"),
        calories_kcal_per_100g=Decimal("165.000"),
        status=CatalogFood.STATUS_PUBLISHED,
        source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
        data_quality_score=95,
    )
    CatalogFoodPortion.objects.create(
        catalog_food=food,
        label="1 porción",
        grams=Decimal("120.000"),
        household_amount=Decimal("1.000"),
        household_measure="unit",
        household_detail="pechuga mediana",
        source="reviewed",
        is_default=True,
    )
    CatalogFoodSource.objects.create(
        catalog_food=food,
        source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
        source_name="Tabla oficial",
        source_food_id="pollo-cocido-release-test",
        source_version="2026",
        license_status=CatalogFoodSource.LICENSE_ALLOWED,
    )
    return food
