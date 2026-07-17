from decimal import Decimal

from django.test import TestCase

from food_catalog.models import CatalogFood, CatalogFoodPortion
from notas.application.queries.solver_food_candidates import build_solver_food_profile
from notas.application.services.food_catalog_snapshots import create_operational_food_snapshot_from_catalog
from nutrition_solver.domain.capabilities import SolverFeatureKey


class SolverCapabilitySnapshotNSO04Tests(TestCase):
    def test_capabilities_cross_only_through_explicit_operational_snapshot(self):
        catalog_food = CatalogFood.objects.create(
            display_name="Snapshot food",
            canonical_name="snapshot food",
            catalog_version="catalog-v2",
            food_group="proteins",
            preparation_state=CatalogFood.PREPARATION_COOKED,
            food_form=CatalogFood.FOOD_FORM_INGREDIENT,
            functional_roles=["primary_protein", "supporting_fat"],
            meal_affinities=["main", "dinner"],
            solver_feature_confidence={"functional_roles": 92, "meal_affinities": 81},
            solver_enabled=True,
            protein_g_per_100g=Decimal("30"),
            carbs_g_per_100g=Decimal("2"),
            fat_g_per_100g=Decimal("8"),
            status=CatalogFood.STATUS_PUBLISHED,
            data_quality_score=95,
        )
        CatalogFoodPortion.objects.create(
            catalog_food=catalog_food,
            label="portion",
            grams=Decimal("100"),
            is_default=True,
        )

        operational = create_operational_food_snapshot_from_catalog(catalog_food).food
        profile = build_solver_food_profile(operational)

        self.assertEqual(operational.solver_capabilities_version, "solver_food_capabilities.v1")
        self.assertEqual(profile.functional_roles, ("primary_protein", "supporting_fat"))
        self.assertEqual(profile.meal_affinities, ("main", "dinner"))
        self.assertEqual(
            profile.feature(SolverFeatureKey.FUNCTIONAL_ROLES).confidence,
            92,
        )
        self.assertNotIn("catalog_food_id", profile.as_dict())

    def test_operational_food_without_curated_roles_uses_identified_derivation(self):
        from notas.domain.models import Food

        food = Food.objects.create(
            name="Derived food",
            protein=25,
            carbs=5,
            fat=5,
            is_global=True,
            solver_enabled=True,
            preparation_state=Food.PREPARATION_READY_TO_EAT,
            data_quality_score=80,
        )

        profile = build_solver_food_profile(food)
        feature = profile.feature(SolverFeatureKey.FUNCTIONAL_ROLES)

        self.assertTrue(feature.derived)
        self.assertEqual(feature.source, "macro_role_rules.v1")
