from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from food_catalog.infrastructure.releases import build_catalog_release
from food_catalog.management.commands.seed_completo_italiano_pilot import PILOT_REF
from food_catalog.models import CatalogFood, CatalogPreparation


@override_settings(ROOT_URLCONF="miapp.catalog_urls")
class CompletoItalianoPilotTests(TestCase):
    def setUp(self):
        for name in ("Palta", "Tomate"):
            CatalogFood.objects.create(
                display_name=name, canonical_name=name.lower(), country="CL",
                status=CatalogFood.STATUS_PUBLISHED,
                preparation_state=CatalogFood.PREPARATION_READY_TO_EAT,
                protein_g_per_100g=Decimal("1"), carbs_g_per_100g=Decimal("2"),
                fat_g_per_100g=Decimal("3"), sodium_mg_per_100g=Decimal("4"),
                allergens=[],
            )

    def test_dry_run_does_not_write(self):
        call_command("seed_completo_italiano_pilot", stdout=StringIO())
        self.assertEqual(CatalogFood.objects.count(), 2)
        self.assertFalse(CatalogPreparation.objects.exists())

    def test_apply_publishes_five_ingredient_preparation_and_retry_is_safe(self):
        call_command("seed_completo_italiano_pilot", apply=True, stdout=StringIO())
        preparation = CatalogPreparation.objects.get(catalog_ref=PILOT_REF)
        version = preparation.current_version
        self.assertEqual(version.yield_g, Decimal("179"))
        self.assertEqual(version.default_portion_g, Decimal("179"))
        self.assertEqual([row["name"] for row in version.ingredients_snapshot], [
            "Pan de completo", "Vienesa tradicional PF", "Palta", "Tomate", "Mayonesa regular",
        ])
        self.assertEqual([Decimal(row["quantity_g"]) for row in version.ingredients_snapshot], [
            Decimal("45"), Decimal("50"), Decimal("40"), Decimal("30"), Decimal("14"),
        ])
        self.assertEqual(version.nutrition["allergens"], ["egg", "gluten", "soy", "wheat"])
        self.assertEqual(CatalogFood.objects.filter(status=CatalogFood.STATUS_PUBLISHED).count(), 5)
        release = build_catalog_release(version="pilot-1")
        self.assertEqual(release.food_count, 5)
        self.assertEqual(len(release.payload["preparations"]), 1)
        self.assertEqual(release.payload["preparations"][0]["catalog_ref"], str(PILOT_REF))

        call_command("seed_completo_italiano_pilot", apply=True, stdout=StringIO())
        self.assertEqual(CatalogPreparation.objects.count(), 1)
        self.assertEqual(CatalogFood.objects.count(), 5)
        self.assertEqual(preparation.versions.count(), 1)

    def test_conflicting_existing_food_aborts_without_changes(self):
        CatalogFood.objects.create(
            display_name="Pan de hot dog", canonical_name="pan de completo", country="CL",
            protein_g_per_100g=Decimal("1"), carbs_g_per_100g=Decimal("2"),
            fat_g_per_100g=Decimal("3"),
        )
        with self.assertRaises(CommandError):
            call_command("seed_completo_italiano_pilot", apply=True, stdout=StringIO())
        self.assertEqual(CatalogFood.objects.count(), 3)
        self.assertFalse(CatalogPreparation.objects.exists())
