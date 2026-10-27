from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from mobile_api.explore import explore_dailyplans_payload
from notas.application.dailyplan_catalog_seed import STARTER_DAILYPLAN_CATALOG
from notas.application.meal_catalog_seed import STARTER_MEAL_CATALOG
from notas.domain.models import DailyPlanCatalogEntry, Food


class DailyPlanCatalogSeedTests(TestCase):
    def setUp(self):
        names = {name for definition in STARTER_MEAL_CATALOG for name, _quantity in definition["foods"]}
        Food.objects.bulk_create([Food(name=name, protein=10, carbs=20, fat=5, is_global=True) for name in names])
        call_command("seed_meal_catalog", apply=True, stdout=StringIO())

    def test_seed_builds_eight_private_plans_with_all_filters_idempotently(self):
        call_command("seed_dailyplan_catalog", apply=True, stdout=StringIO())
        call_command("seed_dailyplan_catalog", apply=True, stdout=StringIO())

        self.assertEqual(len(STARTER_DAILYPLAN_CATALOG), 8)
        self.assertEqual(DailyPlanCatalogEntry.objects.count(), 8)
        self.assertEqual(DailyPlanCatalogEntry.objects.filter(is_published=True).count(), 8)
        self.assertSetEqual(set(DailyPlanCatalogEntry.objects.values_list("dietary_style", flat=True)), {"omnivore", "pescatarian", "vegetarian", "vegan"})
        for entry in DailyPlanCatalogEntry.objects.select_related("dailyplan"):
            self.assertFalse(entry.dailyplan.is_public)
            self.assertFalse(entry.dailyplan.is_draft)
            self.assertIn(entry.dailyplan.dailyplan_meals.count(), (3, 4))
            self.assertTrue(entry.dailyplan.summary_cache)

        viewer = get_user_model().objects.create_user(username="plan-catalog-viewer")
        for style in ("omnivore", "pescatarian", "vegetarian", "vegan"):
            for count in (3, 4):
                page = explore_dailyplans_payload(viewer, dietary_style=style, meal_count=count)
                self.assertEqual(page["total"], 1)
                self.assertEqual(page["items"][0]["meal_count"], count)
