from django.test import SimpleTestCase

from nutrition_solver.application.contracts import OptimizationStatus, SolverConstraint
from nutrition_solver.application.optimizer_v2 import (
    solve_optimization_alternatives,
    solve_optimization_problem,
)
from nutrition_solver.application.problem_v2 import MealSlotProblem, NutrientRange, OptimizationProblemV2
from nutrition_solver.domain.capabilities import SolverFeatureKey
from nutrition_solver.domain.food_profiles import SolverFeatureValue, SolverFoodProfile
from nutrition_solver.domain.meal_grammar import MAIN_PLATE
from nutrition_solver.domain.models import PortionBounds, SolverFood


def _profile(food_id, roles, protein, carbs, fat, kcal):
    return SolverFoodProfile(
        food=SolverFood(food_id, f"food-{food_id}", "balanced", protein, carbs, fat, kcal, PortionBounds(20, 200, 10), False),
        features=(SolverFeatureValue(SolverFeatureKey.FUNCTIONAL_ROLES, tuple(roles), 90, "test"),),
    )


def _daily_problem(*, constraints=()):
    profiles = (
        _profile(1, ("primary_protein",), 25, 0, 5, 145),
        _profile(2, ("primary_protein",), 20, 4, 8, 168),
        _profile(3, ("starch_or_carbohydrate",), 3, 28, 1, 133),
        _profile(4, ("starch_or_carbohydrate",), 5, 20, 2, 118),
    )
    meal_ranges = (
        NutrientRange("kcal", 450, 320, 600, 2),
        NutrientRange("protein", 35, 22, 55, 2),
        NutrientRange("carbs", 50, 30, 80, 1),
        NutrientRange("fat", 12, 4, 30, 1),
    )
    slots = (
        MealSlotProblem("lunch", "main", meal_ranges, (MAIN_PLATE,)),
        MealSlotProblem("dinner", "dinner", meal_ranges, (MAIN_PLATE,)),
    )
    daily_ranges = (
        NutrientRange("kcal", 900, 750, 1050, 3),
        NutrientRange("protein", 70, 55, 90, 3),
    )
    return OptimizationProblemV2(
        profiles,
        slots,
        daily_nutrient_ranges=daily_ranges,
        constraints=constraints,
    )


class NutritionSolverNSO08DailyOptimizationTests(SimpleTestCase):
    def test_daily_ranges_are_enforced_across_meals(self):
        result = solve_optimization_problem(_daily_problem(), backend="cp_sat_v1")

        self.assertNotEqual(result.status, OptimizationStatus.IMPOSSIBLE)
        self.assertGreaterEqual(result.daily_totals["kcal"], 750)
        self.assertLessEqual(result.daily_totals["kcal"], 1050)
        self.assertGreaterEqual(result.daily_totals["protein"], 55)

    def test_hard_repetition_limit_is_global(self):
        constraint = SolverConstraint("max_food_repetitions", "hard", {"count": 1})
        result = solve_optimization_problem(
            _daily_problem(constraints=(constraint,)),
            backend="cp_sat_v1",
        )

        selected = [portion.food_id for meal in result.meals for portion in meal.portions]
        self.assertEqual(len(selected), len(set(selected)))

    def test_returns_distinct_ranked_alternatives(self):
        portfolio = solve_optimization_alternatives(_daily_problem(), count=3)

        signatures = {
            tuple((meal.slot_id, portion.food_id) for meal in result.meals for portion in meal.portions)
            for result in portfolio.alternatives
        }
        self.assertGreaterEqual(len(portfolio.alternatives), 2)
        self.assertEqual(len(signatures), len(portfolio.alternatives))
