from decimal import Decimal

from django.test import TestCase

from food_catalog.application.publication import check_catalog_food_publishable
from food_catalog.application.solver_readiness import (
    build_catalog_solver_profile,
    check_catalog_food_solver_ready,
)
from food_catalog.models import CatalogFood, CatalogFoodPortion, CatalogFoodSource


class CatalogSolverReadinessTests(TestCase):
    def test_disabled_food_is_not_solver_ready_but_can_still_be_curated(self):
        catalog_food = _create_catalog_food(solver_enabled=False)
        _add_allowed_source(catalog_food)
        _add_default_portion(catalog_food)

        readiness = check_catalog_food_solver_ready(catalog_food)
        publication = check_catalog_food_publishable(catalog_food)

        self.assertFalse(readiness.is_ready)
        self.assertIn("solver_enabled is false", readiness.errors)
        self.assertTrue(publication.can_publish)

    def test_solver_enabled_food_requires_explicit_preparation_state(self):
        catalog_food = _create_catalog_food(
            solver_enabled=True,
            preparation_state=CatalogFood.PREPARATION_UNKNOWN,
        )
        _add_allowed_source(catalog_food)
        _add_default_portion(catalog_food)

        readiness = check_catalog_food_solver_ready(catalog_food)
        publication = check_catalog_food_publishable(catalog_food)

        self.assertFalse(readiness.is_ready)
        self.assertIn("preparation_state must be explicit for solver-enabled foods", readiness.errors)
        self.assertFalse(publication.can_publish)
        self.assertIn(
            "solver readiness: preparation_state must be explicit for solver-enabled foods",
            publication.errors,
        )

    def test_solver_profile_infers_safe_portion_bounds_from_default_portion(self):
        catalog_food = _create_catalog_food(
            solver_enabled=True,
            preparation_state=CatalogFood.PREPARATION_COOKED,
        )
        _add_default_portion(catalog_food, grams=Decimal("120.000"))

        profile = build_catalog_solver_profile(catalog_food)

        self.assertEqual(profile.default_portion_g, Decimal("120.000"))
        self.assertEqual(profile.min_portion_g, Decimal("60.000"))
        self.assertEqual(profile.max_portion_g, Decimal("300.000"))
        self.assertEqual(profile.portion_step_g, Decimal("10.000"))
        self.assertEqual(profile.preparation_state, CatalogFood.PREPARATION_COOKED)
        self.assertTrue(profile.solver_enabled)

    def test_explicit_solver_portion_bounds_are_validated(self):
        catalog_food = _create_catalog_food(
            solver_enabled=True,
            preparation_state=CatalogFood.PREPARATION_READY_TO_EAT,
            solver_min_portion_g=Decimal("200.000"),
            solver_max_portion_g=Decimal("80.000"),
            solver_portion_step_g=Decimal("5.000"),
        )
        _add_default_portion(catalog_food, grams=Decimal("100.000"))

        readiness = check_catalog_food_solver_ready(catalog_food)

        self.assertFalse(readiness.is_ready)
        self.assertIn("minimum solver portion cannot exceed default portion", readiness.errors)
        self.assertIn("maximum solver portion cannot be lower than default portion", readiness.errors)
        self.assertIn("minimum solver portion cannot exceed maximum portion", readiness.errors)


def _create_catalog_food(
    *,
    solver_enabled: bool,
    preparation_state: str = CatalogFood.PREPARATION_READY_TO_EAT,
    solver_min_portion_g=None,
    solver_max_portion_g=None,
    solver_portion_step_g=None,
) -> CatalogFood:
    return CatalogFood.objects.create(
        display_name="Avena",
        canonical_name="avena",
        food_group="cereals",
        food_subgroup="oats",
        preparation_state=preparation_state,
        solver_enabled=solver_enabled,
        solver_min_portion_g=solver_min_portion_g,
        solver_max_portion_g=solver_max_portion_g,
        solver_portion_step_g=solver_portion_step_g,
        protein_g_per_100g=Decimal("16.900"),
        carbs_g_per_100g=Decimal("66.300"),
        fat_g_per_100g=Decimal("6.900"),
        status=CatalogFood.STATUS_REVIEWED,
        source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        data_quality_score=90,
    )


def _add_default_portion(catalog_food: CatalogFood, *, grams: Decimal = Decimal("100.000")) -> CatalogFoodPortion:
    return CatalogFoodPortion.objects.create(
        catalog_food=catalog_food,
        label="1 porción",
        grams=grams,
        is_default=True,
    )


def _add_allowed_source(catalog_food: CatalogFood) -> CatalogFoodSource:
    return CatalogFoodSource.objects.create(
        catalog_food=catalog_food,
        source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        source_name="manual-curation",
        source_food_id=f"manual-{catalog_food.pk}",
        license_status=CatalogFoodSource.LICENSE_ALLOWED,
    )
