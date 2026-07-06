import json

from django.test import SimpleTestCase

from notas.application.nutrition_engine.contracts import (
    OptimizationInput,
    OptimizationResult,
    OptimizationScoringConfig,
    OptimizationStatus,
    assess_optimization_status,
    impossible_optimization_result,
    optimize_meal_portions,
)
from notas.application.nutrition_engine.models import (
    MacroTarget,
    PortionBounds,
    PortionSolverDiagnostics,
    PortionSolverResult,
    SolverFood,
)


class NutritionEngineOptimizationStatusTests(SimpleTestCase):
    def test_status_assessment_explains_optimal_threshold(self):
        assessment = assess_optimization_status(
            {"kcal": 3.4, "protein": -7.5, "carbs": 2.1, "fat": None}
        )
        payload = assessment.as_dict()

        json.dumps(payload)
        self.assertEqual(assessment.status, OptimizationStatus.OPTIMAL)
        self.assertEqual(payload["reason_code"], "within_optimal_tolerance")
        self.assertEqual(payload["worst_macro"], "protein")
        self.assertEqual(payload["worst_deviation_percent"], 7.5)
        self.assertEqual(payload["applied_tolerance_percent"], 8.0)

    def test_status_assessment_explains_acceptable_threshold(self):
        assessment = assess_optimization_status(
            {"kcal": -12.5, "protein": 4.0, "carbs": 9.0, "fat": 15.5}
        )
        payload = assessment.as_dict()

        json.dumps(payload)
        self.assertEqual(assessment.status, OptimizationStatus.ACCEPTABLE)
        self.assertEqual(payload["reason_code"], "within_acceptable_tolerance")
        self.assertEqual(payload["worst_macro"], "fat")
        self.assertEqual(payload["applied_tolerance_percent"], 18.0)

    def test_status_assessment_explains_partial_threshold(self):
        assessment = assess_optimization_status(
            {"kcal": -11.0, "protein": -21.0, "carbs": -9.0, "fat": 2.0}
        )
        payload = assessment.as_dict()

        json.dumps(payload)
        self.assertEqual(assessment.status, OptimizationStatus.PARTIAL)
        self.assertEqual(payload["reason_code"], "outside_acceptable_tolerance")
        self.assertEqual(payload["worst_macro"], "protein")
        self.assertEqual(payload["applied_tolerance_percent"], 18.0)

    def test_custom_scoring_config_changes_status_boundary(self):
        assessment = assess_optimization_status(
            {"kcal": 12.0, "protein": 9.0, "carbs": 4.0, "fat": 3.0},
            scoring_config=OptimizationScoringConfig(
                optimal_tolerance_percent=5,
                acceptable_tolerance_percent=10,
            ),
        )

        self.assertEqual(assessment.status, OptimizationStatus.PARTIAL)
        self.assertEqual(assessment.reason_code, "outside_acceptable_tolerance")
        self.assertEqual(assessment.applied_tolerance_percent, 10.0)

    def test_result_payload_includes_assessment_scoring_config_and_issue_counts(self):
        portion_result = PortionSolverResult(
            portions=[],
            diagnostics=PortionSolverDiagnostics(
                score=123.45,
                iterations=8,
                target=MacroTarget(kcal=500, protein=40, carbs=60, fat=12),
                actual=MacroTarget(kcal=455, protein=34, carbs=58, fat=13),
                diff=MacroTarget(kcal=-45, protein=-6, carbs=-2, fat=1),
                diff_percent={"kcal": -9, "protein": -15, "carbs": -3.33, "fat": 8.33},
                notes=["Diagnóstico de prueba."],
            ),
        )
        result = OptimizationResult.from_portion_solver_result(
            portion_result,
            warnings=("soft_constraint_not_fully_satisfied",),
        )
        payload = result.as_dict()

        json.dumps(payload)
        self.assertEqual(result.status, OptimizationStatus.ACCEPTABLE)
        self.assertEqual(payload["diagnostics"]["assessment"]["reason_code"], "within_acceptable_tolerance")
        self.assertEqual(payload["diagnostics"]["assessment"]["worst_macro"], "protein")
        self.assertEqual(payload["diagnostics"]["score_direction"], "lower_is_better")
        self.assertEqual(payload["diagnostics"]["scoring_config"]["acceptable_tolerance_percent"], 18.0)
        self.assertEqual(payload["diagnostics"]["issue_counts"], {"warnings": 1, "errors": 0})

    def test_impossible_payload_has_explicit_reason_assessment(self):
        result = impossible_optimization_result(
            target=MacroTarget(kcal=700, protein=55, carbs=90, fat=18),
            reason="solver_requires_candidate_foods",
            warnings=("optimization_input_missing_meal_slots",),
        )
        payload = result.as_dict()

        json.dumps(payload)
        self.assertEqual(payload["status"], "impossible")
        self.assertEqual(payload["diagnostics"]["assessment"]["status"], "impossible")
        self.assertEqual(payload["diagnostics"]["assessment"]["reason_code"], "solver_requires_candidate_foods")
        self.assertEqual(payload["diagnostics"]["issue_counts"], {"warnings": 1, "errors": 1})

    def test_contract_optimizer_accepts_custom_scoring_config(self):
        result = optimize_meal_portions(
            optimization_input=OptimizationInput(
                target=MacroTarget(kcal=430, protein=40, carbs=56, fat=5),
                candidate_foods=(self._protein_food(), self._carb_food()),
                meal_slots=("Almuerzo",),
            ),
            scoring_config=OptimizationScoringConfig(
                optimal_tolerance_percent=4,
                acceptable_tolerance_percent=12,
            ),
        )
        payload = result.as_dict()

        json.dumps(payload)
        self.assertEqual(payload["diagnostics"]["scoring_config"]["optimal_tolerance_percent"], 4.0)
        self.assertEqual(payload["diagnostics"]["scoring_config"]["acceptable_tolerance_percent"], 12.0)
        self.assertIn(payload["diagnostics"]["assessment"]["reason_code"], {
            "within_optimal_tolerance",
            "within_acceptable_tolerance",
            "outside_acceptable_tolerance",
        })

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
