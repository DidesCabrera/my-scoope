from django.test import SimpleTestCase

from nutrition_solver.application.optimizer_v2 import OptimizationBackend, solve_optimization_problem
from nutrition_solver.application.problem_v2 import MealSlotProblem, NutrientRange, OptimizationProblemV2
from nutrition_solver.application.quality import assess_optimization_quality
from nutrition_solver.application.shadow import compare_solver_backends
from nutrition_solver.domain.capabilities import SolverFeatureKey
from nutrition_solver.domain.food_profiles import SolverFeatureValue, SolverFoodProfile
from nutrition_solver.domain.meal_grammar import MAIN_PLATE
from nutrition_solver.domain.models import PortionBounds, SolverFood


def _profile(food_id, roles, protein, carbs, fat, kcal):
    return SolverFoodProfile(
        food=SolverFood(food_id, f"food-{food_id}", "balanced", protein, carbs, fat, kcal, PortionBounds(20, 200, 10), False),
        features=(SolverFeatureValue(SolverFeatureKey.FUNCTIONAL_ROLES, tuple(roles), 90, "test"),),
    )


def _problem():
    profiles = (
        _profile(1, ("primary_protein",), 25, 0, 5, 145),
        _profile(2, ("starch_or_carbohydrate",), 3, 28, 1, 133),
        _profile(3, ("starch_or_carbohydrate",), 5, 20, 2, 118),
    )
    ranges = (
        NutrientRange("kcal", 500, 400, 600, 2),
        NutrientRange("protein", 40, 30, 55, 2),
        NutrientRange("carbs", 55, 40, 75, 1),
        NutrientRange("fat", 12, 5, 25, 1),
    )
    return OptimizationProblemV2(profiles, (MealSlotProblem("lunch", "main", ranges, (MAIN_PLATE,)),))


class NutritionSolverNSO09ShadowQualityTests(SimpleTestCase):
    def test_quality_explains_nutrition_and_function_separately(self):
        problem = _problem()
        result = solve_optimization_problem(problem, backend="cp_sat_v1")

        quality = assess_optimization_quality(problem, result)

        self.assertGreater(quality.nutritional_score, 0)
        self.assertEqual(quality.functional_score, 100)
        self.assertEqual(len(quality.explanations), 2)

    def test_shadow_comparison_does_not_change_active_result(self):
        comparison = compare_solver_backends(
            _problem(),
            active_backend=OptimizationBackend.HEURISTIC_V2,
            shadow_backend=OptimizationBackend.CP_SAT_V1,
        )

        self.assertEqual(comparison.active_result.backend, OptimizationBackend.HEURISTIC_V2)
        self.assertEqual(comparison.shadow_result.backend, OptimizationBackend.CP_SAT_V1)
        self.assertIn("nutritional_score_delta", comparison.as_telemetry())
        self.assertGreaterEqual(comparison.selection_overlap, 0)

    def test_impossible_shadow_is_classified_as_hard_regression(self):
        problem = _problem()
        impossible_slot = MealSlotProblem(
            "lunch",
            "main",
            (NutrientRange("protein", 500, 490, 510),),
            (MAIN_PLATE,),
        )
        impossible_problem = OptimizationProblemV2(problem.food_profiles, (impossible_slot,))

        comparison = compare_solver_backends(
            impossible_problem,
            active_backend="heuristic_v2",
            shadow_backend="cp_sat_v1",
        )

        self.assertTrue(comparison.hard_regression)
        self.assertIn("shadow_became_impossible", comparison.regression_reasons)
