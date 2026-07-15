from pathlib import Path

from django.test import SimpleTestCase


class MCPDailyPlanBuildProposalFlowDocumentationTests(SimpleTestCase):
    DOC_PATH = Path("docs/archive/mcp_stage_logs/mcp_dailyplan_build_proposal_flow_test.md")

    def test_documentation_exists(self):
        self.assertTrue(self.DOC_PATH.exists())

    def test_documentation_mentions_dailyplan_build_tool(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("create_validated_dailyplan_build_proposal", content)
        self.assertIn("create_dailyplan", content)

    def test_documentation_mentions_food_catalog(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("list_food_catalog", content)
        self.assertIn("food_id", content)

    def test_documentation_mentions_simulation(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("validation_summary", content)
        self.assertIn("simulation", content)
        self.assertIn("dailyplan", content)
        self.assertIn("kpis", content)

    def test_documentation_mentions_auth_note(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("MYSCOOPE_INTERNAL_API_TOKEN", content)
        self.assertIn("MYSCOOPE_API_AUTH_TOKEN", content)

    def test_documentation_mentions_product_boundary(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("does not", content)
        self.assertIn("create final DailyPlan records", content)
        self.assertIn("create final Meal records", content)
        self.assertIn("apply proposals", content)

    def test_documentation_mentions_next_stage(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("Etapa 4", content)
        self.assertIn("Human Review UI for Nutrition Proposals", content)
