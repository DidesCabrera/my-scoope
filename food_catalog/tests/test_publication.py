from decimal import Decimal

from django.test import TestCase

from food_catalog.application.publication import check_catalog_food_publishable
from food_catalog.models import CatalogFood, CatalogFoodPortion, CatalogFoodSource


class CatalogFoodPublicationCheckTests(TestCase):
    def test_publishable_food_requires_source_and_default_portion(self):
        catalog_food = _create_catalog_food()

        check = check_catalog_food_publishable(catalog_food)

        self.assertFalse(check.can_publish)
        self.assertIn("at least one traceable source is required", check.errors)
        self.assertIn("at least one serving/portion option is required", check.errors)

    def test_publishable_food_requires_reviewed_or_verified_status(self):
        catalog_food = _create_catalog_food(status=CatalogFood.STATUS_PENDING_REVIEW)
        _add_allowed_source(catalog_food)
        CatalogFoodPortion.objects.create(
            catalog_food=catalog_food,
            label="100 g",
            grams=Decimal("100.000"),
            is_default=True,
        )

        check = check_catalog_food_publishable(catalog_food)

        self.assertFalse(check.can_publish)
        self.assertIn("status must be reviewed or verified before publication", check.errors)

    def test_publishable_food_accepts_allowed_source_and_default_portion(self):
        catalog_food = _create_catalog_food()
        _add_allowed_source(catalog_food)
        CatalogFoodPortion.objects.create(
            catalog_food=catalog_food,
            label="100 g",
            grams=Decimal("100.000"),
            is_default=True,
        )

        check = check_catalog_food_publishable(catalog_food)

        self.assertTrue(check.can_publish)
        self.assertEqual(check.errors, ())

    def test_publishable_food_blocks_low_quality_score(self):
        catalog_food = _create_catalog_food(data_quality_score=40)
        _add_allowed_source(catalog_food)
        CatalogFoodPortion.objects.create(
            catalog_food=catalog_food,
            label="100 g",
            grams=Decimal("100.000"),
            is_default=True,
        )

        check = check_catalog_food_publishable(catalog_food)

        self.assertFalse(check.can_publish)
        self.assertIn("data_quality_score must be at least 70", check.errors)

    def test_publishable_food_blocks_restricted_sources(self):
        catalog_food = _create_catalog_food()
        CatalogFoodSource.objects.create(
            catalog_food=catalog_food,
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="restricted-source",
            source_food_id="restricted-1",
            license_status=CatalogFoodSource.LICENSE_RESTRICTED,
        )
        CatalogFoodPortion.objects.create(
            catalog_food=catalog_food,
            label="100 g",
            grams=Decimal("100.000"),
            is_default=True,
        )

        check = check_catalog_food_publishable(catalog_food)

        self.assertFalse(check.can_publish)
        self.assertIn("at least one source with allowed or reviewed license is required", check.errors)


def _create_catalog_food(*, data_quality_score: int = 90, status: str = CatalogFood.STATUS_REVIEWED) -> CatalogFood:
    return CatalogFood.objects.create(
        display_name="Avena",
        canonical_name="avena",
        protein_g_per_100g=Decimal("16.900"),
        carbs_g_per_100g=Decimal("66.300"),
        fat_g_per_100g=Decimal("6.900"),
        status=status,
        source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        data_quality_score=data_quality_score,
    )


def _add_allowed_source(catalog_food: CatalogFood) -> CatalogFoodSource:
    return CatalogFoodSource.objects.create(
        catalog_food=catalog_food,
        source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        source_name="manual-curation",
        source_food_id=f"manual-{catalog_food.pk}",
        license_status=CatalogFoodSource.LICENSE_ALLOWED,
    )
