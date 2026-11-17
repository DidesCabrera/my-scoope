from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from food_catalog.infrastructure.releases import approve_catalog_release, build_catalog_release, release_envelope
from food_catalog.models import CatalogFood, CatalogFoodPortion, CatalogFoodSource


class ApprovedOilsPublicationTests(TestCase):
    def test_usda_oils_pass_publication_gate_and_are_idempotent(self):
        call_command("seed_approved_oils_20261117")
        call_command("seed_approved_oils_20261117")
        self.assertEqual(CatalogFood.objects.filter(display_name__in=["Aceite de maravilla", "Aceite de coco"]).count(), 2)
        for name, fdc_id, fat in (
            ("Aceite de maravilla", "171025", 100),
            ("Aceite de coco", "171412", 99.06),
        ):
            food = CatalogFood.objects.get(display_name=name)
            self.assertEqual(food.status, CatalogFood.STATUS_PUBLISHED)
            self.assertEqual(float(food.fat_g_per_100g), fat)
            self.assertTrue(CatalogFoodSource.objects.filter(catalog_food=food, source_food_id=fdc_id).exists())
            self.assertEqual(CatalogFoodPortion.objects.get(catalog_food=food, is_default=True).grams, Decimal("13.6"))
        release = approve_catalog_release(build_catalog_release(version="test.oils.20261117"))
        self.assertEqual(release_envelope(release)["release"]["food_count"], 2)
