from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from food_catalog.application.curation import (
    allowed_next_statuses,
    transition_catalog_food_status,
)
from food_catalog.models import CatalogFood, CatalogFoodPortion, CatalogFoodSource


class CatalogFoodCurationWorkflowTests(TestCase):
    def test_candidate_can_move_to_pending_review(self):
        catalog_food = _create_catalog_food(status=CatalogFood.STATUS_MANUAL_CANDIDATE)

        result = transition_catalog_food_status(
            catalog_food,
            CatalogFood.STATUS_PENDING_REVIEW,
        )

        self.assertTrue(result.changed)
        catalog_food.refresh_from_db()
        self.assertEqual(catalog_food.status, CatalogFood.STATUS_PENDING_REVIEW)

    def test_pending_review_can_be_marked_reviewed_with_reviewer(self):
        user = get_user_model().objects.create_user(username="curator")
        catalog_food = _create_catalog_food(status=CatalogFood.STATUS_PENDING_REVIEW)

        result = transition_catalog_food_status(
            catalog_food,
            CatalogFood.STATUS_REVIEWED,
            user=user,
        )

        self.assertTrue(result.changed)
        catalog_food.refresh_from_db()
        self.assertEqual(catalog_food.status, CatalogFood.STATUS_REVIEWED)
        self.assertEqual(catalog_food.reviewed_by, user)
        self.assertIsNotNone(catalog_food.reviewed_at)

    def test_invalid_transition_is_blocked(self):
        catalog_food = _create_catalog_food(status=CatalogFood.STATUS_ARCHIVED)

        result = transition_catalog_food_status(
            catalog_food,
            CatalogFood.STATUS_PUBLISHED,
        )

        self.assertFalse(result.changed)
        self.assertIn("cannot transition from archived to published", result.errors)
        catalog_food.refresh_from_db()
        self.assertEqual(catalog_food.status, CatalogFood.STATUS_ARCHIVED)

    def test_publish_transition_requires_publication_guard(self):
        catalog_food = _create_catalog_food(status=CatalogFood.STATUS_VERIFIED)

        result = transition_catalog_food_status(
            catalog_food,
            CatalogFood.STATUS_PUBLISHED,
        )

        self.assertFalse(result.changed)
        self.assertIn("at least one traceable source is required", result.errors)
        self.assertIn("at least one serving/portion option is required", result.errors)
        catalog_food.refresh_from_db()
        self.assertEqual(catalog_food.status, CatalogFood.STATUS_VERIFIED)

    def test_publish_transition_marks_publish_timestamp(self):
        user = get_user_model().objects.create_user(username="curator")
        catalog_food = _create_catalog_food(status=CatalogFood.STATUS_VERIFIED)
        _make_publishable(catalog_food)

        result = transition_catalog_food_status(
            catalog_food,
            CatalogFood.STATUS_PUBLISHED,
            user=user,
        )

        self.assertTrue(result.changed)
        catalog_food.refresh_from_db()
        self.assertEqual(catalog_food.status, CatalogFood.STATUS_PUBLISHED)
        self.assertEqual(catalog_food.reviewed_by, user)
        self.assertIsNotNone(catalog_food.reviewed_at)
        self.assertIsNotNone(catalog_food.published_at)

    def test_allowed_next_statuses_exposes_workflow_contract(self):
        self.assertIn(
            CatalogFood.STATUS_REVIEWED,
            allowed_next_statuses(CatalogFood.STATUS_PENDING_REVIEW),
        )
        self.assertNotIn(
            CatalogFood.STATUS_PUBLISHED,
            allowed_next_statuses(CatalogFood.STATUS_MANUAL_CANDIDATE),
        )


def _create_catalog_food(*, status: str) -> CatalogFood:
    return CatalogFood.objects.create(
        display_name="Avena",
        canonical_name="avena",
        protein_g_per_100g=Decimal("16.900"),
        carbs_g_per_100g=Decimal("66.300"),
        fat_g_per_100g=Decimal("6.900"),
        status=status,
        source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        data_quality_score=90,
    )


def _make_publishable(catalog_food: CatalogFood) -> None:
    CatalogFoodSource.objects.create(
        catalog_food=catalog_food,
        source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        source_name="manual-curation",
        source_food_id=f"manual-{catalog_food.pk}",
        license_status=CatalogFoodSource.LICENSE_ALLOWED,
    )
    CatalogFoodPortion.objects.create(
        catalog_food=catalog_food,
        label="100 g",
        grams=Decimal("100.000"),
        is_default=True,
    )
