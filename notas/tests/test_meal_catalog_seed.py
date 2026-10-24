from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from notas.application.meal_catalog_seed import STARTER_MEAL_CATALOG
from notas.domain.models import Food, Meal, MealCatalogEntry


class MealCatalogSeedTests(TestCase):
    def setUp(self):
        names = {name for definition in STARTER_MEAL_CATALOG for name, _quantity in definition["foods"]}
        Food.objects.bulk_create([
            Food(name=name, protein=10, carbs=20, fat=5, is_global=True)
            for name in names
        ])

    def test_seed_builds_exactly_thirty_private_catalog_meals_idempotently(self):
        call_command("seed_meal_catalog", apply=True, stdout=StringIO())
        call_command("seed_meal_catalog", apply=True, stdout=StringIO())

        self.assertEqual(len(STARTER_MEAL_CATALOG), 30)
        self.assertEqual(MealCatalogEntry.objects.count(), 30)
        self.assertEqual(MealCatalogEntry.objects.filter(is_published=True).count(), 30)
        self.assertEqual(Meal.objects.filter(catalog_entry__isnull=False, is_public=True).count(), 0)
        self.assertSetEqual(
            set(MealCatalogEntry.objects.values_list("dietary_style", flat=True)),
            {"omnivore", "pescatarian", "vegetarian", "vegan"},
        )
        self.assertSetEqual(
            set(MealCatalogEntry.objects.values_list("occasion", flat=True)),
            {"breakfast", "lunch", "dinner", "snack", "pre_workout", "post_workout"},
        )
