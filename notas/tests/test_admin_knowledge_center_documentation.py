from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_CENTER = ROOT / "docs" / "00_current" / "features" / "admin_knowledge"


class AdminKnowledgeCenterDocumentationTests(SimpleTestCase):
    def test_all_guides_are_explicitly_human_and_non_authoritative(self):
        for path in KNOWLEDGE_CENTER.glob("*.md"):
            content = path.read_text()
            with self.subTest(path=path.name):
                self.assertIn("Role: human_reference", content)
                self.assertIn("Authority: non_authoritative", content)
                self.assertIn("Update-Policy: explicit_user_request_only", content)

    def test_index_links_food_catalog_and_solver_guides(self):
        content = (KNOWLEDGE_CENTER / "README.md").read_text()

        self.assertIn("AI Assistant y paridad del sistema", content)
        self.assertIn("Food Catalog para el Solver", content)
        self.assertIn("Nutrition Solver", content)
        self.assertIn("CatalogFood curado", content)
        self.assertIn("pending_review", content)
        self.assertIn("No es una fuente de verdad", content)
        self.assertIn("Solo se actualiza", content)

    def test_ai_assistant_guide_documents_latest_parity_and_snapshot_boundary(self):
        content = (KNOWLEDGE_CENTER / "ai_assistant.md").read_text()

        for expected in (
            "ai_assistant.application.tools.registry",
            "ai_assistant.domain.capabilities",
            "AIPreparedAction",
            "snapshots independientes",
            "AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS",
            "staff-only",
        ):
            self.assertIn(expected, content)
        self.assertIn("no modifica", content)

    def test_food_catalog_guide_documents_versioned_capabilities_and_snapshot_boundary(self):
        content = (KNOWLEDGE_CENTER / "food_catalog.md").read_text()

        for expected in (
            "functional_roles",
            "meal_affinities",
            "solver_feature_confidence",
            "solver_food_capabilities.v1",
            "data_quality_score >= 70",
            "notas.Food.solver_capabilities_version",
            "macro_role_rules.v1",
        ):
            self.assertIn(expected, content)
        self.assertIn("nunca recibe `catalog_ref`", content)

    def test_solver_guide_documents_v2_runtime_quality_and_rollback(self):
        content = (KNOWLEDGE_CENTER / "nutrition_solver.md").read_text()

        for expected in (
            "Optimization V2",
            "main_plate",
            "cp_sat_v1",
            "heuristic_v2",
            "cp_sat_infeasible",
            "Calidad y telemetría",
            "NUTRITION_SOLVER_SHADOW_ENABLED",
        ):
            self.assertIn(expected, content)
        self.assertIn("no se relajan restricciones duras", content)
