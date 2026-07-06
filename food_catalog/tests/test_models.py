from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from food_catalog.models import (
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodPortion,
    CatalogFoodSource,
    CatalogImportBatch,
)


class CatalogFoodModelTests(TestCase):
    def test_catalog_food_is_master_record_not_operational_food(self):
        food = CatalogFood.objects.create(
            display_name="Pechuga de pollo cocida",
            canonical_name="pechuga pollo cocida",
            food_group="meats",
            food_subgroup="poultry",
            protein_g_per_100g=Decimal("31.000"),
            carbs_g_per_100g=Decimal("0.000"),
            fat_g_per_100g=Decimal("3.600"),
            calories_kcal_per_100g=Decimal("165.000"),
            status=CatalogFood.STATUS_PUBLISHED,
            source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
            data_quality_score=95,
        )

        self.assertTrue(food.catalog_ref)
        self.assertEqual(str(food), "Pechuga de pollo cocida")
        self.assertTrue(food.is_published)
        self.assertEqual(food.macro_calories_kcal, Decimal("156.400"))

    def test_catalog_food_rejects_invalid_quality_score(self):
        food = CatalogFood(
            display_name="Invalid food",
            protein_g_per_100g=Decimal("1"),
            carbs_g_per_100g=Decimal("1"),
            fat_g_per_100g=Decimal("1"),
            data_quality_score=101,
        )

        with self.assertRaises(ValidationError):
            food.full_clean()

    def test_related_catalog_metadata_models_are_owned_by_food_catalog(self):
        food = CatalogFood.objects.create(
            display_name="Avena tradicional",
            canonical_name="avena tradicional",
            protein_g_per_100g=Decimal("13.500"),
            carbs_g_per_100g=Decimal("68.000"),
            fat_g_per_100g=Decimal("7.000"),
            source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
        )
        batch = CatalogImportBatch.objects.create(
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="manual-curation",
            status=CatalogImportBatch.STATUS_COMPLETED,
            total_rows=1,
            imported_rows=1,
        )
        portion = CatalogFoodPortion.objects.create(
            catalog_food=food,
            label="1 taza",
            grams=Decimal("80.000"),
            is_default=True,
        )
        alias = CatalogFoodAlias.objects.create(
            catalog_food=food,
            name="oats",
            normalized_name="oats",
            language="en",
        )
        source = CatalogFoodSource.objects.create(
            catalog_food=food,
            import_batch=batch,
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="manual-curation",
            source_food_id="avena-001",
            license_status=CatalogFoodSource.LICENSE_ALLOWED,
        )

        self.assertEqual(food.portions.get(), portion)
        self.assertEqual(food.aliases.get(), alias)
        self.assertEqual(food.sources.get(), source)
        self.assertEqual(batch.food_sources.get(), source)
        self.assertIn("1 taza", str(portion))
        self.assertIn("oats", str(alias))
        self.assertIn("avena-001", str(source))
