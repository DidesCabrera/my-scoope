import json

from django.test import SimpleTestCase

from nutrition_solver.application.contracts import (
    OptimizationInput,
    OptimizationResult,
    OptimizationStatus,
    SolverConstraint,
    impossible_optimization_result,
)
from nutrition_solver.domain.models import MacroTarget, PortionBounds, SolverFood
from nutrition_solver.application.portion_solver import solve_meal_portions


class NutritionEngineOptimizationContractsTests(SimpleTestCase):
    def test_optimization_input_is_serializable_and_keeps_solver_boundary_pure(self):
        candidate = SolverFood(
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
        contract = OptimizationInput(
            target=MacroTarget(kcal=420, protein=35, carbs=45, fat=12),
            candidate_foods=[candidate],
            meal_slots=["Almuerzo"],
            constraints=[
                SolverConstraint(
                    constraint_type="exclude_food_group",
                    severity="soft",
                    payload={"group": "fried"},
                    message="Evitar frituras en esta propuesta.",
                )
            ],
            preferences={"goal": "cut"},
            context={"source": "test"},
        )

        payload = contract.as_dict()

        json.dumps(payload)
        self.assertEqual(payload["target"]["protein"], 35.0)
        self.assertEqual(payload["candidate_foods"][0]["food_id"], 1)
        self.assertEqual(payload["candidate_foods"][0]["bounds"]["step_g"], 5.0)
        self.assertEqual(payload["constraints"][0]["type"], "exclude_food_group")
        self.assertNotIn("catalog_food_id", payload["candidate_foods"][0])
        self.assertNotIn("request", payload)

    def test_optimization_result_wraps_existing_portion_solver_result(self):
        portion_result = solve_meal_portions(
            foods=[
                SolverFood(
                    food_id=1,
                    name="Pechuga de pollo",
                    role="protein",
                    protein_per_100g=31,
                    carbs_per_100g=0,
                    fat_per_100g=3,
                    kcal_per_100g=151,
                    bounds=PortionBounds(90, 260, 5),
                    required=True,
                ),
                SolverFood(
                    food_id=2,
                    name="Arroz cocido",
                    role="carb",
                    protein_per_100g=2.5,
                    carbs_per_100g=28,
                    fat_per_100g=0.2,
                    kcal_per_100g=124,
                    bounds=PortionBounds(45, 240, 5),
                    required=True,
                ),
            ],
            target=MacroTarget(kcal=430, protein=40, carbs=56, fat=5),
        )

        optimization = OptimizationResult.from_portion_solver_result(
            portion_result,
            metadata={"meal_slot": "Almuerzo"},
        )
        payload = optimization.as_dict()

        json.dumps(payload)
        self.assertIn(optimization.status, {
            OptimizationStatus.OPTIMAL,
            OptimizationStatus.ACCEPTABLE,
            OptimizationStatus.PARTIAL,
        })
        self.assertEqual(payload["status"], optimization.status.value)
        self.assertEqual(payload["diagnostics"]["metadata"]["meal_slot"], "Almuerzo")
        self.assertGreater(len(payload["portions"]), 0)
        self.assertIn("diff_percent", payload["diagnostics"])

    def test_impossible_result_is_machine_readable_without_throwing(self):
        result = impossible_optimization_result(
            target=MacroTarget(kcal=700, protein=55, carbs=90, fat=18),
            reason="solver_requires_candidate_foods",
            metadata={"candidate_count": 0},
        )
        payload = result.as_dict()

        json.dumps(payload)
        self.assertEqual(result.status, OptimizationStatus.IMPOSSIBLE)
        self.assertEqual(payload["status"], "impossible")
        self.assertEqual(payload["portions"], [])
        self.assertIn("solver_requires_candidate_foods", payload["diagnostics"]["errors"])
        self.assertEqual(payload["diagnostics"]["metadata"]["candidate_count"], 0)
