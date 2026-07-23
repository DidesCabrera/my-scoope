from decimal import Decimal

from django.test import TestCase

from food_catalog.application.solver_readiness import build_catalog_solver_profile
from food_catalog.models import CatalogFood, CatalogFoodPortion


class FoodCatalogNSO03SolverCapabilitiesTests(TestCase):
    def test_curated_capabilities_are_normalized_into_solver_profile(self):
        food = CatalogFood.objects.create(
            display_name="Food",
            canonical_name="food",
            food_group="group",
            preparation_state=CatalogFood.PREPARATION_READY_TO_EAT,
            food_form=CatalogFood.FOOD_FORM_INGREDIENT,
            functional_roles=[" Primary_Protein ", "supporting_protein", "primary_protein"],
            meal_affinities=["Breakfast", "snack"],
            dietary_tags=["vegetarian"],
            allergens=["milk"],
            preparation_effort=CatalogFood.PREPARATION_EFFORT_LOW,
            cost_band=CatalogFood.COST_BAND_MEDIUM,
            solver_enabled=True,
            solver_feature_confidence={"functional_roles": 88, "meal_affinities": "72"},
            protein_g_per_100g=Decimal("20"),
            carbs_g_per_100g=Decimal("5"),
            fat_g_per_100g=Decimal("8"),
            data_quality_score=90,
        )
        CatalogFoodPortion.objects.create(catalog_food=food, label="portion", grams=100, is_default=True)

        profile = build_catalog_solver_profile(food)

        self.assertEqual(profile.functional_roles, ("primary_protein", "supporting_protein"))
        self.assertEqual(profile.meal_affinities, ("breakfast", "snack"))
        self.assertEqual(profile.feature_confidence["functional_roles"], 88)
        self.assertEqual(profile.food_form, "ingredient")

    def test_open_capabilities_default_to_empty_not_invented_values(self):
        food = CatalogFood.objects.create(
            display_name="Food",
            food_group="group",
            preparation_state=CatalogFood.PREPARATION_COOKED,
            protein_g_per_100g=Decimal("10"),
            carbs_g_per_100g=Decimal("10"),
            fat_g_per_100g=Decimal("10"),
        )

        profile = build_catalog_solver_profile(food)

        self.assertEqual(profile.functional_roles, ())
        self.assertEqual(profile.meal_affinities, ())
        self.assertEqual(profile.feature_confidence, {})
