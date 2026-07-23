import json

from django.test import SimpleTestCase

from nutrition_solver.application.problem_v2 import (
    MealSlotProblem,
    NutrientRange,
    OptimizationProblemV2,
)
from nutrition_solver.domain.food_profiles import SolverFeatureValue, SolverFoodProfile
from nutrition_solver.domain.capabilities import SolverFeatureKey
from nutrition_solver.domain.meal_grammar import MAIN_PLATE, assess_meal_grammar
from nutrition_solver.domain.models import PortionBounds, SolverFood


def _profile(food_id, roles):
    food = SolverFood(food_id, f"food-{food_id}", "balanced", 10, 10, 5, 125, PortionBounds(10, 200, 5), False)
    return SolverFoodProfile(
        food=food,
        features=(SolverFeatureValue(SolverFeatureKey.FUNCTIONAL_ROLES, tuple(roles), 90, "test"),),
    )


class NutritionSolverNSO05ProblemAndGrammarTests(SimpleTestCase):
    def test_main_plate_accepts_capability_groups_not_exclusive_categories(self):
        profiles = (
            _profile(1, ("primary_protein", "supporting_fat")),
            _profile(2, ("starch_or_carbohydrate",)),
        )

        assessment = assess_meal_grammar(MAIN_PLATE, profiles)

        self.assertTrue(assessment.is_valid)
        self.assertIn("supporting_fat", assessment.role_coverage)

    def test_missing_required_group_is_structured(self):
        assessment = assess_meal_grammar(MAIN_PLATE, (_profile(1, ("primary_protein",)),))

        self.assertFalse(assessment.is_valid)
        self.assertIn(("starch_or_carbohydrate", "mixed_food"), assessment.missing_role_groups)

    def test_problem_v2_is_serializable_and_uses_ranges(self):
        profiles = (_profile(1, ("primary_protein",)), _profile(2, ("starch_or_carbohydrate",)))
        slot = MealSlotProblem(
            slot_id="lunch",
            meal_kind="main",
            nutrient_ranges=(NutrientRange("kcal", 600, 540, 660, 2.0),),
            allowed_archetypes=(MAIN_PLATE,),
        )
        problem = OptimizationProblemV2(food_profiles=profiles, meal_slots=(slot,))

        payload = problem.as_dict()
        json.dumps(payload)
        self.assertEqual(payload["meal_slots"][0]["nutrient_ranges"][0]["minimum"], 540)

    def test_invalid_nutrient_range_is_rejected(self):
        with self.assertRaisesMessage(ValueError, "nutrient_range_order_invalid"):
            NutrientRange("protein", 40, 50, 45)
