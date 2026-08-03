import json

from django.test import SimpleTestCase

from nutrition_solver.application.contracts import (
    OptimizationInput,
    OptimizationResult,
    OptimizationStatus,
    SolverConstraint,
    impossible_optimization_result,
    optimize_meal_portions,
)
from nutrition_solver.domain.models import (
    MacroTarget,
    PortionBounds,
    PortionSolverDiagnostics,
    PortionSolverResult,
    SolverFood,
)


class NutritionEngineOptimizationScenarioTests(SimpleTestCase):
    def test_contract_optimizer_returns_base_solution_without_warnings(self):
        result = optimize_meal_portions(
            OptimizationInput(
                target=MacroTarget(kcal=430, protein=40, carbs=56, fat=5),
                candidate_foods=(
                    self._protein_food(),
                    self._carb_food(),
                ),
                meal_slots=("Almuerzo",),
            )
        )
        payload = result.as_dict()

        json.dumps(payload)
        self.assertIn(result.status, {
            OptimizationStatus.OPTIMAL,
            OptimizationStatus.ACCEPTABLE,
            OptimizationStatus.PARTIAL,
        })
        self.assertGreater(len(result.portions), 0)
        self.assertEqual(payload["diagnostics"]["warnings"], [])
        self.assertEqual(payload["diagnostics"]["errors"], [])
        self.assertEqual(payload["diagnostics"]["metadata"]["candidate_count"], 2)
        self.assertEqual(payload["diagnostics"]["metadata"]["meal_slots"], ["Almuerzo"])

    def test_contract_optimizer_preserves_input_warnings(self):
        result = optimize_meal_portions(
            OptimizationInput(
                target=MacroTarget(kcal=430, protein=40, carbs=56, fat=5),
                candidate_foods=(
                    self._protein_food(),
                    self._carb_food(),
                ),
                constraints=(
                    SolverConstraint(
                        constraint_type="prefer_food_group",
                        severity="soft",
                        payload={"group": "vegetables"},
                    ),
                ),
            )
        )
        payload = result.as_dict()

        json.dumps(payload)
        self.assertIn("optimization_input_missing_meal_slots", payload["diagnostics"]["warnings"])
        self.assertIn("optimization_input_contains_soft_constraints", payload["diagnostics"]["warnings"])
        self.assertEqual(payload["diagnostics"]["metadata"]["constraint_count"], 1)

    def test_partial_result_is_machine_readable_when_deviation_is_large(self):
        target = MacroTarget(kcal=500, protein=40, carbs=60, fat=12)
        actual = MacroTarget(kcal=250, protein=12, carbs=20, fat=4)
        portion_result = PortionSolverResult(
            portions=[],
            diagnostics=PortionSolverDiagnostics(
                score=812.5,
                iterations=3,
                target=target,
                actual=actual,
                diff=MacroTarget(kcal=-250, protein=-28, carbs=-40, fat=-8),
                diff_percent={"kcal": -50, "protein": -70, "carbs": -66.67, "fat": -66.67},
                notes=["La propuesta requiere ajuste fino antes de aplicarse como plan final."],
            ),
        )
        result = OptimizationResult.from_portion_solver_result(portion_result)
        payload = result.as_dict()

        json.dumps(payload)
        self.assertEqual(result.status, OptimizationStatus.PARTIAL)
        self.assertEqual(payload["status"], "partial")
        self.assertEqual(payload["diagnostics"]["diff_percent"]["protein"], -70.0)
        self.assertEqual(payload["diagnostics"]["errors"], [])

    def test_contract_optimizer_converts_empty_candidates_to_impossible_result(self):
        result = optimize_meal_portions(
            OptimizationInput(
                target=MacroTarget(kcal=700, protein=55, carbs=90, fat=18),
                candidate_foods=(),
                meal_slots=("Cena",),
            )
        )
        payload = result.as_dict()

        json.dumps(payload)
        self.assertEqual(result.status, OptimizationStatus.IMPOSSIBLE)
        self.assertEqual(payload["status"], "impossible")
        self.assertEqual(payload["portions"], [])
        self.assertIn("solver_requires_candidate_foods", payload["diagnostics"]["errors"])
        self.assertEqual(payload["diagnostics"]["metadata"]["candidate_count"], 0)
        self.assertEqual(payload["diagnostics"]["metadata"]["meal_slots"], ["Cena"])

    def test_impossible_result_can_carry_warnings_and_metadata(self):
        result = impossible_optimization_result(
            target=MacroTarget(kcal=700, protein=55, carbs=90, fat=18),
            reason="portion_solver_requires_usable_foods",
            warnings=("optimization_input_missing_meal_slots",),
            metadata={"candidate_count": 2},
        )
        payload = result.as_dict()

        json.dumps(payload)
        self.assertEqual(payload["diagnostics"]["warnings"], ["optimization_input_missing_meal_slots"])
        self.assertIn("portion_solver_requires_usable_foods", payload["diagnostics"]["errors"])
        self.assertEqual(payload["diagnostics"]["metadata"]["candidate_count"], 2)

    def _protein_food(self) -> SolverFood:
        return SolverFood(
            food_id=1,
            name="Pechuga de pollo",
            role="protein",
            protein_per_100g=31,
            carbs_per_100g=0,
            fat_per_100g=3,
            kcal_per_100g=151,
            bounds=PortionBounds(90, 260, 5),
            required=True,
        )

    def _carb_food(self) -> SolverFood:
        return SolverFood(
            food_id=2,
            name="Arroz cocido",
            role="carb",
            protein_per_100g=2.5,
            carbs_per_100g=28,
            fat_per_100g=0.2,
            kcal_per_100g=124,
            bounds=PortionBounds(45, 240, 5),
            required=True,
        )
