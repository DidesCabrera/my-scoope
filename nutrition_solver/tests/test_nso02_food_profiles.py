import json

from django.test import SimpleTestCase

from nutrition_solver.domain.capabilities import SolverFeatureKey
from nutrition_solver.domain.food_profiles import (
    SolverFeatureValue,
    SolverFoodProfile,
    derive_macro_role_features,
)
from nutrition_solver.domain.models import PortionBounds, SolverFood


class NutritionSolverNSO02FoodProfilesTests(SimpleTestCase):
    def setUp(self):
        self.food = SolverFood(
            1,
            "Test food",
            "protein",
            30,
            10,
            8,
            232,
            PortionBounds(80, 240, 5),
        )

    def test_profile_keeps_values_provenance_and_confidence(self):
        profile = SolverFoodProfile(
            food=self.food,
            features=(
                SolverFeatureValue(
                    SolverFeatureKey.PREPARATION_STATE,
                    "cooked",
                    95,
                    "operational_snapshot",
                    "catalog-v3",
                ),
            ),
        )

        payload = profile.as_dict()
        json.dumps(payload)
        self.assertEqual(payload["features"][0]["source"], "operational_snapshot")
        self.assertEqual(profile.availability()[SolverFeatureKey.PREPARATION_STATE].confidence, 95)

    def test_food_can_expose_multiple_functional_roles(self):
        derived = derive_macro_role_features(self.food)
        profile = SolverFoodProfile(food=self.food, features=(derived,))

        self.assertIn("primary_protein", profile.functional_roles)
        self.assertTrue(derived.derived)

    def test_duplicate_feature_is_rejected(self):
        feature = SolverFeatureValue(SolverFeatureKey.FOOD_FORM, "ingredient", 80, "catalog")

        with self.assertRaisesMessage(ValueError, "solver_food_profile_duplicate_feature"):
            SolverFoodProfile(food=self.food, features=(feature, feature))

    def test_missing_feature_has_no_invented_default(self):
        profile = SolverFoodProfile(food=self.food)

        self.assertIsNone(profile.feature(SolverFeatureKey.COST_BAND))
        self.assertEqual(profile.meal_affinities, ())
