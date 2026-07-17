from django.test import SimpleTestCase

from nutrition_solver.application.contracts import OptimizationStatus, SolverConstraint
from nutrition_solver.application.optimizer_v2 import OptimizationBackend, solve_optimization_problem
from nutrition_solver.application.problem_v2 import MealSlotProblem, NutrientRange, OptimizationProblemV2
from nutrition_solver.domain.capabilities import SolverFeatureKey
from nutrition_solver.domain.food_profiles import SolverFeatureValue, SolverFoodProfile
from nutrition_solver.domain.meal_grammar import MAIN_PLATE
from nutrition_solver.domain.models import PortionBounds, SolverFood


def _profile(food_id, roles, protein, carbs, fat, kcal, *, step=10):
    return SolverFoodProfile(
        food=SolverFood(food_id, f"food-{food_id}", "balanced", protein, carbs, fat, kcal, PortionBounds(20, 200, step), False),
        features=(SolverFeatureValue(SolverFeatureKey.FUNCTIONAL_ROLES, tuple(roles), 90, "test"),),
    )


def _problem(*, constraints=()):
    profiles = (
        _profile(1, ("primary_protein",), 25, 0, 5, 145),
        _profile(2, ("starch_or_carbohydrate",), 3, 28, 1, 133),
        _profile(3, ("starch_or_carbohydrate",), 5, 20, 2, 118),
    )
    ranges = (
        NutrientRange("kcal", 500, 400, 600, 2),
        NutrientRange("protein", 40, 30, 55, 3),
        NutrientRange("carbs", 55, 40, 75, 1),
        NutrientRange("fat", 12, 5, 25, 1),
    )
    slot = MealSlotProblem("lunch", "main", ranges, (MAIN_PLATE,))
    return OptimizationProblemV2(profiles, (slot,), constraints=constraints)


class NutritionSolverNSO07CpSatBackendTests(SimpleTestCase):
    def test_cp_sat_enforces_portion_steps_and_hard_ranges(self):
        result = solve_optimization_problem(_problem(), backend=OptimizationBackend.CP_SAT_V1)

        self.assertIn(result.status, (OptimizationStatus.OPTIMAL, OptimizationStatus.ACCEPTABLE))
        self.assertGreaterEqual(result.meals[0].nutrient_totals["protein"], 30)
        self.assertTrue(all(portion.quantity_g % 10 == 0 for portion in result.meals[0].portions))

    def test_hard_exclusion_is_enforced(self):
        constraint = SolverConstraint("exclude_food_id", "hard", {"food_id": 2})
        result = solve_optimization_problem(_problem(constraints=(constraint,)), backend="cp_sat_v1")

        self.assertNotIn(2, {portion.food_id for portion in result.meals[0].portions})

    def test_repeated_runs_are_deterministic(self):
        first = solve_optimization_problem(_problem(), backend="cp_sat_v1")
        second = solve_optimization_problem(_problem(), backend="cp_sat_v1")

        self.assertEqual(
            [portion.as_dict() for portion in first.meals[0].portions],
            [portion.as_dict() for portion in second.meals[0].portions],
        )

    def test_infeasible_hard_constraints_are_not_silently_relaxed(self):
        impossible_range = (NutrientRange("protein", 500, 490, 510, 1),)
        slot = MealSlotProblem("lunch", "main", impossible_range, (MAIN_PLATE,))
        problem = OptimizationProblemV2(_problem().food_profiles, (slot,))

        result = solve_optimization_problem(problem, backend="cp_sat_v1")

        self.assertEqual(result.status, OptimizationStatus.IMPOSSIBLE)
        self.assertEqual(result.diagnostics["reason"], "cp_sat_infeasible")
