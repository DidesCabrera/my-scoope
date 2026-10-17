from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from food_catalog.infrastructure.usda_portion_publication import (
    FALLBACK_SOURCE,
    PORTION_SOURCE,
    prepare_usda_sr_legacy_publication,
)
from food_catalog.models import CatalogFood, CatalogFoodSource


class UsdaPortionPublicationPreparationTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_user(
            username="catalog-operator",
            email="operator@example.com",
        )

    def test_apply_adds_official_and_fallback_portions_and_verifies_complete_wave(self):
        pear = self._food("Pera cruda", "pera-cruda", "169118")
        fava = self._food("Habas cocidas", "habas-cocidas", "170378")

        dry_run = prepare_usda_sr_legacy_publication()

        self.assertEqual(dry_run.foods, 2)
        self.assertEqual(dry_run.official_foods, 1)
        self.assertEqual(dry_run.fallback_foods, 1)
        self.assertEqual(dry_run.changed_foods, 0)
        self.assertFalse(pear.portions.exists())

        result = prepare_usda_sr_legacy_publication(
            apply=True,
            actor=self.actor,
            reason="Approved USDA publication wave.",
        )

        pear.refresh_from_db()
        fava.refresh_from_db()
        self.assertEqual(result.changed_foods, 2)
        self.assertEqual(pear.status, CatalogFood.STATUS_VERIFIED)
        self.assertEqual(fava.status, CatalogFood.STATUS_VERIFIED)
        self.assertEqual(pear.portions.filter(source=PORTION_SOURCE).count(), 6)
        self.assertEqual(pear.portions.filter(is_default=True).count(), 1)
        self.assertEqual(fava.portions.get().label, "100 g (base nutricional)")
        self.assertEqual(fava.portions.get().grams, Decimal("100.000"))
        self.assertEqual(fava.portions.get().source, FALLBACK_SOURCE)
        self.assertTrue(fava.portions.get().is_default)
        self.assertIn(
            "operational_portion_fallback",
            fava.sources.get().evidence_payload,
        )

    def test_apply_requires_authenticated_actor_and_reason(self):
        self._food("Pera cruda", "pera-cruda", "169118")

        with self.assertRaisesRegex(ValueError, "reason is required"):
            prepare_usda_sr_legacy_publication(apply=True, actor=self.actor)
        with self.assertRaisesRegex(ValueError, "authenticated actor is required"):
            prepare_usda_sr_legacy_publication(apply=True, reason="Approved wave")

    def _food(self, display_name, canonical_name, source_food_id):
        food = CatalogFood.objects.create(
            display_name=display_name,
            canonical_name=canonical_name,
            protein_g_per_100g=Decimal("2.000"),
            carbs_g_per_100g=Decimal("20.000"),
            fat_g_per_100g=Decimal("1.000"),
            status=CatalogFood.STATUS_PENDING_REVIEW,
            source_type=CatalogFood.SOURCE_USDA,
            data_quality_score=90,
        )
        CatalogFoodSource.objects.create(
            catalog_food=food,
            source_type=CatalogFood.SOURCE_USDA,
            source_name="USDA FoodData Central",
            source_food_id=source_food_id,
            source_dataset="sr_legacy",
            source_version="2018-04",
            license_status=CatalogFoodSource.LICENSE_ALLOWED,
        )
        return food
