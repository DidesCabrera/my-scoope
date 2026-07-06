import json

from django.test import SimpleTestCase

from nutrition_solver.application.contracts import (
    OptimizationInput,
    OptimizationResult,
    OptimizationScoringConfig,
    OptimizationStatus,
    SolverConstraint,
    assess_optimization_status,
    impossible_optimization_result,
)
from nutrition_solver.domain.models import (
    MacroTarget,
    PortionBounds,
    PortionSolverDiagnostics,
    PortionSolverResult,
    SolverFood,
)


class NutritionSolverPureContractsBoundaryTests(SimpleTestCase):
    def test_domain_models_are_owned_by_nutrition_solver(self):
        target = MacroTarget(kcal=430, protein=40, carbs=56, fat=5)
        candidate = SolverFood(
            food_id=1,
            name="Pechuga de pollo",
            role="protein",
            protein_per_100g=31,
            carbs_per_100g=0,
            fat_per_100g=3,
            kcal_per_100g=151,
            bounds=PortionBounds(90, 260, 5),
        )

        self.assertEqual(MacroTarget.__module__, "nutrition_solver.domain.models")
        self.assertEqual(SolverFood.__module__, "nutrition_solver.domain.models")
        self.assertEqual(target.as_dict()["protein"], 40.0)
        self.assertEqual(candidate.macros_for_quantity(100).protein, 31)

    def test_optimization_contracts_are_serializable_inside_new_app(self):
        contract = OptimizationInput(
            target=MacroTarget(kcal=430, protein=40, carbs=56, fat=5),
            candidate_foods=(
                SolverFood(
                    food_id=1,
                    name="Pechuga de pollo",
                    role="protein",
                    protein_per_100g=31,
                    carbs_per_100g=0,
                    fat_per_100g=3,
                    kcal_per_100g=151,
                    bounds=PortionBounds(90, 260, 5),
                ),
            ),
            meal_slots=("Almuerzo",),
            constraints=(
                SolverConstraint(
                    constraint_type="avoid_role",
                    severity="soft",
                    payload={"role": "fat"},
                ),
            ),
        )
        payload = contract.as_dict()

        json.dumps(payload)
        self.assertEqual(OptimizationInput.__module__, "nutrition_solver.application.contracts")
        self.assertEqual(SolverConstraint.__module__, "nutrition_solver.application.contracts")
        self.assertEqual(payload["candidate_foods"][0]["bounds"]["maximum_g"], 260.0)
        self.assertNotIn("catalog_food_id", payload["candidate_foods"][0])

    def test_result_assessment_lives_in_new_app_without_notas_adapter(self):
        assessment = assess_optimization_status(
            {"kcal": -9, "protein": -15, "carbs": -3.33, "fat": 8.33},
            scoring_config=OptimizationScoringConfig(
                optimal_tolerance_percent=8,
                acceptable_tolerance_percent=18,
            ),
        )

        self.assertEqual(assessment.status, OptimizationStatus.ACCEPTABLE)
        self.assertEqual(assessment.reason_code, "within_acceptable_tolerance")
        self.assertEqual(assessment.worst_macro, "protein")

    def test_result_can_wrap_domain_portion_result_in_new_app(self):
        portion_result = PortionSolverResult(
            portions=(),
            diagnostics=PortionSolverDiagnostics(
                score=123.45,
                iterations=8,
                target=MacroTarget(kcal=500, protein=40, carbs=60, fat=12),
                actual=MacroTarget(kcal=455, protein=34, carbs=58, fat=13),
                diff=MacroTarget(kcal=-45, protein=-6, carbs=-2, fat=1),
                diff_percent={"kcal": -9, "protein": -15, "carbs": -3.33, "fat": 8.33},
            ),
        )
        result = OptimizationResult.from_portion_solver_result(portion_result)
        payload = result.as_dict()

        json.dumps(payload)
        self.assertEqual(result.status, OptimizationStatus.ACCEPTABLE)
        self.assertEqual(payload["diagnostics"]["assessment"]["worst_macro"], "protein")


    def test_extracted_core_python_files_do_not_import_product_boundaries(self):
        app_root = __import__("pathlib").Path(__file__).resolve().parents[1]
        forbidden_fragments = (
            "from notas",
            "import notas",
            "from food_catalog",
            "import food_catalog",
            "from ai_assistant",
            "import ai_assistant",
        )
        offenders = []

        for path in sorted((app_root / "domain").glob("**/*.py")) + sorted((app_root / "application").glob("**/*.py")):
            content = path.read_text()
            for fragment in forbidden_fragments:
                if fragment in content:
                    offenders.append(f"{path.relative_to(app_root)} contains {fragment!r}")

        self.assertEqual(offenders, [])

    def test_impossible_result_is_available_without_importing_notas_engine(self):
        result = impossible_optimization_result(
            target=MacroTarget(kcal=700, protein=55, carbs=90, fat=18),
            reason="solver_requires_candidate_foods",
            metadata={"candidate_count": 0},
        )
        payload = result.as_dict()

        json.dumps(payload)
        self.assertEqual(result.status, OptimizationStatus.IMPOSSIBLE)
        self.assertEqual(payload["diagnostics"]["assessment"]["reason_code"], "solver_requires_candidate_foods")
