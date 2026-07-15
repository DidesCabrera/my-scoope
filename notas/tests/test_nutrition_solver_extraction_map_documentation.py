from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parents[2]
EXTRACTION_MAP = ROOT / "docs" / "00_current" / "architecture" / "nutrition_solver_extraction_map.md"
PLANNING_DOC = ROOT / "docs" / "10_active_cycles" / "nutrition_solver_app_cycle.md"
DECISION_DOC = ROOT / "docs" / "20_decisions" / "0044-nutrition-solver-extraction-start.md"
S6_DECISION_DOC = ROOT / "docs" / "20_decisions" / "0046-nutrition-solver-pure-contracts-moved.md"
S7_DECISION_DOC = ROOT / "docs" / "20_decisions" / "0047-nutrition-solver-portion-solver-validators-moved.md"
S8_DECISION_DOC = ROOT / "docs" / "20_decisions" / "0048-nutrition-solver-operational-food-adapter.md"
S9_DECISION_DOC = ROOT / "docs" / "20_decisions" / "0049-nutrition-solver-ai-assistant-preview-tool.md"
S10_DECISION_DOC = ROOT / "docs" / "00_current" / "architecture" / "nutrition_solver_extraction_map.md"
LEGACY_CONTRACTS_MODULE = ROOT / "notas" / "application" / "nutrition_engine" / "contracts.py"
SOLVER_CONTRACTS_MODULE = ROOT / "nutrition_solver" / "application" / "contracts.py"
SOLVER_MODELS_MODULE = ROOT / "nutrition_solver" / "domain" / "models.py"
LEGACY_PORTION_SOLVER_MODULE = ROOT / "notas" / "application" / "nutrition_engine" / "portion_solver.py"
LEGACY_VALIDATORS_MODULE = ROOT / "notas" / "application" / "nutrition_engine" / "validators.py"
SOLVER_PORTION_SOLVER_MODULE = ROOT / "nutrition_solver" / "application" / "portion_solver.py"
SOLVER_VALIDATORS_MODULE = ROOT / "nutrition_solver" / "application" / "validators.py"
SOLVER_CANDIDATES_QUERY = ROOT / "notas" / "application" / "queries" / "solver_food_candidates.py"
AI_TOOL_REGISTRY = ROOT / "ai_assistant" / "application" / "tools" / "registry.py"
AI_TOOL_EXECUTOR = ROOT / "ai_assistant" / "application" / "tools" / "executor.py"
AI_READ_TOOLS = ROOT / "notas" / "application" / "ai_tools" / "read_tools.py"
AI_PROPOSAL_TOOLS = ROOT / "notas" / "application" / "ai_tools" / "proposal_tools.py"
SOLVER_MEAL_PROPOSALS = ROOT / "notas" / "application" / "proposals" / "solver_meal_proposals.py"
NUTRITION_SOLVER_APP = ROOT / "nutrition_solver"


class NutritionSolverExtractionMapDocumentationTests(SimpleTestCase):
    def test_extraction_map_records_current_engine_modules_and_s10_state(self):
        content = EXTRACTION_MAP.read_text()

        self.assertIn("Status: completed", content)
        self.assertIn("Patch: S10 closure", content)
        self.assertIn("S1 did **not** move code", content)
        self.assertIn("deterministic portion solver and strict validators", content)
        self.assertIn("notas/application/nutrition_engine/", content)

        for module_name in (
            "models.py",
            "target_estimator.py",
            "meal_templates.py",
            "candidate_selector.py",
            "portion_solver.py",
            "validators.py",
            "contracts.py",
        ):
            self.assertIn(module_name, content)

    def test_extraction_map_protects_solver_input_boundary(self):
        content = EXTRACTION_MAP.read_text()

        self.assertIn("food_catalog.CatalogFood", content)
        self.assertIn("notas.Food", content)
        self.assertIn("solver candidate adapter/query", content)
        self.assertIn("Disallowed direct solver inputs", content)
        self.assertIn("ExternalFoodReference", content)
        self.assertIn("request/user/session/template objects", content)

    def test_planning_and_decision_docs_mark_cycle_as_completed(self):
        planning = PLANNING_DOC.read_text()
        decision = DECISION_DOC.read_text()

        self.assertIn("Status: completed", planning)
        self.assertIn("S1", planning)
        self.assertIn("S2: completado", planning)
        self.assertIn("S3: completado", planning)
        self.assertIn("S4: completado", planning)
        self.assertIn("S5: completado", planning)
        self.assertIn("S6: completado", planning)
        self.assertIn("S7: completado", planning)
        self.assertIn("S8: completado", planning)
        self.assertIn("S9: completado", planning)
        self.assertIn("S10: completado", planning)
        self.assertIn("S11: cancelado/diferido", planning)
        self.assertIn("Status: accepted", decision)
        self.assertIn("does not create the `nutrition_solver` Django app", decision)

    def test_s2_contracts_exist_and_are_documented(self):
        content = EXTRACTION_MAP.read_text()
        contracts = SOLVER_CONTRACTS_MODULE.read_text()

        self.assertIn("S2 adds an optimization-level contract module", content)
        self.assertIn("OptimizationInput", content)
        self.assertIn("OptimizationResult", content)
        self.assertIn("does not", content)
        self.assertIn("change the deterministic portion solver search algorithm", content)

        for contract_name in (
            "OptimizationStatus",
            "SolverConstraint",
            "OptimizationInput",
            "OptimizationDiagnostics",
            "OptimizationResult",
        ):
            self.assertIn(f"class {contract_name}", contracts)

    def test_s3_documents_contract_wrapper(self):
        content = EXTRACTION_MAP.read_text()
        solver_contracts = SOLVER_CONTRACTS_MODULE.read_text()

        self.assertIn("S3 keeps the implementation inside", content)
        self.assertIn("optimize_meal_portions(OptimizationInput) -> OptimizationResult", content)
        self.assertIn("base solvable meal scenario", content)
        self.assertIn("partial result status", content)
        self.assertIn("impossible result", content)
        self.assertIn("def optimize_meal_portions", solver_contracts)
        self.assertIn("except PortionSolverError", solver_contracts)

    def test_s4_documents_explicit_status_assessment(self):
        content = EXTRACTION_MAP.read_text()
        contracts = SOLVER_CONTRACTS_MODULE.read_text()

        self.assertIn("S4 makes the optimization result vocabulary more explicit", content)
        self.assertIn("OptimizationScoringConfig", content)
        self.assertIn("OptimizationStatusAssessment", content)
        self.assertIn("assess_optimization_status", content)
        self.assertIn("issue_counts", content)
        self.assertIn("does not", content)
        self.assertIn("change the deterministic portion solver search algorithm", content)

        for contract_name in (
            "OptimizationScoringConfig",
            "OptimizationStatusAssessment",
        ):
            self.assertIn(f"class {contract_name}", contracts)

        self.assertIn("def assess_optimization_status", contracts)
        self.assertIn("score_direction", contracts)

    def test_s5_documents_physical_app_shell(self):
        content = EXTRACTION_MAP.read_text()
        planning = PLANNING_DOC.read_text()

        self.assertIn("S5 creates the physical Django app boundary", content)
        self.assertIn("nutrition_solver.apps.NutritionSolverConfig", content)
        self.assertIn("S5 intentionally keeps the active deterministic implementation", content)
        self.assertIn("notas/application/nutrition_engine/", content)
        self.assertIn("S6: completado", planning)

        for relative_path in (
            "__init__.py",
            "apps.py",
            "models.py",
            "admin.py",
            "migrations/__init__.py",
            "README.md",
        ):
            self.assertTrue(
                (NUTRITION_SOLVER_APP / relative_path).exists(),
                msg=f"Missing nutrition_solver/{relative_path}",
            )

    def test_s6_documents_pure_contract_move_with_compatibility_bridges(self):
        content = EXTRACTION_MAP.read_text()
        decision = S6_DECISION_DOC.read_text()
        legacy_contracts = LEGACY_CONTRACTS_MODULE.read_text()
        solver_contracts = SOLVER_CONTRACTS_MODULE.read_text()
        solver_models = SOLVER_MODELS_MODULE.read_text()

        self.assertIn("S6 begins the physical extraction", content)
        self.assertIn("nutrition_solver/domain/models.py", content)
        self.assertIn("nutrition_solver/application/contracts.py", content)
        self.assertIn("legacy modules remain as compatibility bridges", content)
        self.assertIn("That wrapper stays in `notas.application.nutrition_engine.contracts`", decision)
        self.assertIn("Status: accepted", decision)
        self.assertIn("Patch: S6", decision)
        self.assertIn("from nutrition_solver.application.contracts import", legacy_contracts)
        self.assertIn("from nutrition_solver.domain.models import", solver_contracts)
        self.assertIn("class MacroTarget", solver_models)


    def test_s7_documents_solver_and_validator_move_with_compatibility_bridges(self):
        content = EXTRACTION_MAP.read_text()
        decision = S7_DECISION_DOC.read_text()
        legacy_contracts = LEGACY_CONTRACTS_MODULE.read_text()
        legacy_portion_solver = LEGACY_PORTION_SOLVER_MODULE.read_text()
        legacy_validators = LEGACY_VALIDATORS_MODULE.read_text()
        solver_contracts = SOLVER_CONTRACTS_MODULE.read_text()
        solver_portion_solver = SOLVER_PORTION_SOLVER_MODULE.read_text()
        solver_validators = SOLVER_VALIDATORS_MODULE.read_text()

        self.assertIn("S7 moves the first executable deterministic solver layer", content)
        self.assertIn("nutrition_solver/application/portion_solver.py", content)
        self.assertIn("nutrition_solver/application/validators.py", content)
        self.assertIn("Patch: S7", decision)
        self.assertIn("from nutrition_solver.application.portion_solver import", legacy_portion_solver)
        self.assertIn("from nutrition_solver.application.validators import", legacy_validators)
        self.assertIn("from nutrition_solver.application.contracts import", legacy_contracts)
        self.assertIn("def optimize_meal_portions", solver_contracts)
        self.assertIn("def solve_meal_portions", solver_portion_solver)
        self.assertIn("def validate_generated_dailyplan", solver_validators)

    def test_s8_documents_operational_food_adapter(self):
        content = EXTRACTION_MAP.read_text()
        planning = PLANNING_DOC.read_text()
        decision = S8_DECISION_DOC.read_text()
        query = SOLVER_CANDIDATES_QUERY.read_text()

        self.assertIn("S8 creates the operational food adapter", content)
        self.assertIn("notas/application/queries/solver_food_candidates.py", content)
        self.assertIn("S8: completado", planning)
        self.assertIn("Patch S8", decision)
        self.assertIn("def list_solver_food_candidates", query)
        self.assertIn("provider payloads", query)
        self.assertIn("never exposes Food Catalog IDs", query)

    def test_s9_documents_ai_assistant_preview_tool(self):
        content = EXTRACTION_MAP.read_text()
        planning = PLANNING_DOC.read_text()
        decision = S9_DECISION_DOC.read_text()
        registry = AI_TOOL_REGISTRY.read_text()
        executor = AI_TOOL_EXECUTOR.read_text()
        read_tools = AI_READ_TOOLS.read_text()

        self.assertIn("S9 exposes the first AI Assistant read/preview boundary", content)
        self.assertIn("preview_nutrition_solver_candidates", content)
        self.assertIn("S9: completado", planning)
        self.assertIn("Status: accepted", decision)
        self.assertIn("TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES", registry)
        self.assertIn("TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES", executor)
        self.assertIn("def preview_nutrition_solver_candidates_tool", read_tools)
        self.assertIn("catalog_fields_exposed", read_tools)

    def test_s10_documents_reviewable_solver_meal_proposal(self):
        content = EXTRACTION_MAP.read_text()
        planning = PLANNING_DOC.read_text()
        decision = S10_DECISION_DOC.read_text()
        registry = AI_TOOL_REGISTRY.read_text()
        proposal_tools = AI_PROPOSAL_TOOLS.read_text()
        service = SOLVER_MEAL_PROPOSALS.read_text()

        self.assertIn("S10 additions", content)
        self.assertIn("create_nutrition_solver_meal_proposal", content)
        self.assertIn("NutritionProposal(status=pending_review)", content)
        self.assertIn("S10: completado", planning)
        self.assertIn("Status: completed", decision)
        self.assertIn("create_solver_generated_meal_proposal", decision)
        self.assertIn("TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL", registry)
        self.assertIn("create_nutrition_solver_meal_proposal_tool", proposal_tools)
        self.assertIn("def create_solver_generated_meal_proposal", service)
        self.assertIn("catalog_fields_exposed", service)
