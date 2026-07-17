from django.test import SimpleTestCase

from nutrition_solver.application.contracts import (
    DEFAULT_OPTIMIZATION_SCORING_CONFIG,
    OptimizationStatus,
    infer_optimization_status,
)
from nutrition_solver.application.portion_solver import (
    DEFAULT_PORTION_SOLVER_CONFIG,
    solve_meal_portions,
)
from nutrition_solver.domain.models import MacroTarget, PortionBounds, SolverFood


class NutritionSolverNSO00BaselineTests(SimpleTestCase):
    def test_heuristic_v2_configuration_is_frozen(self):
        config = DEFAULT_PORTION_SOLVER_CONFIG

        self.assertEqual(config.max_iterations, 220)
        self.assertEqual(config.protein_weight, 3.0)
        self.assertEqual(config.kcal_weight, 2.4)
        self.assertEqual(config.carbs_weight, 1.35)
        self.assertEqual(config.fat_weight, 1.25)

    def test_status_thresholds_are_frozen(self):
        scoring = DEFAULT_OPTIMIZATION_SCORING_CONFIG

        self.assertEqual(scoring.optimal_tolerance_percent, 8.0)
        self.assertEqual(scoring.acceptable_tolerance_percent, 18.0)

    def test_balanced_meal_golden_scenario_is_deterministic(self):
        foods = [
            SolverFood(1, "Protein", "protein", 30, 0, 4, 156, PortionBounds(80, 240, 5)),
            SolverFood(2, "Carb", "carb", 4, 28, 1, 137, PortionBounds(50, 300, 5)),
            SolverFood(3, "Fat", "fat", 0, 0, 100, 900, PortionBounds(5, 30, 5), required=False),
        ]
        target = MacroTarget(kcal=600, protein=45, carbs=75, fat=14)

        first = solve_meal_portions(foods=foods, target=target)
        second = solve_meal_portions(foods=foods, target=target)

        self.assertEqual(first.as_dict(), second.as_dict())
        self.assertLessEqual(first.diagnostics.iterations, 220)
        self.assertNotEqual(
            infer_optimization_status(first.diagnostics),
            OptimizationStatus.IMPOSSIBLE,
        )

    def test_optional_food_can_remain_absent(self):
        foods = [
            SolverFood(1, "Balanced", "protein", 25, 40, 10, 350, PortionBounds(100, 200, 5)),
            SolverFood(2, "Optional fat", "fat", 0, 0, 100, 900, PortionBounds(5, 30, 5), required=False),
        ]

        result = solve_meal_portions(
            foods=foods,
            target=MacroTarget(kcal=350, protein=25, carbs=40, fat=10),
        )

        self.assertEqual([portion.food_id for portion in result.portions], [1])
