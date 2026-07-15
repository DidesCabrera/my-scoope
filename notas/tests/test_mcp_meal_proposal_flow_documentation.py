from pathlib import Path

from django.test import SimpleTestCase


class MCPMealProposalFlowDocumentationTests(SimpleTestCase):
    DOC_PATH = Path("docs/archive/mcp_stage_logs/mcp_meal_proposal_flow_test.md")

    def test_documentation_exists(self):
        self.assertTrue(self.DOC_PATH.exists())

    def test_documentation_mentions_food_catalog_tool(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("list_food_catalog", content)
        self.assertIn("food_id", content)

    def test_documentation_mentions_meal_proposal_tool(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("create_validated_meal_proposal", content)
        self.assertIn("create_meal", content)

    def test_documentation_mentions_simulation(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("validation_summary", content)
        self.assertIn("simulation", content)
        self.assertIn("kpis", content)

    def test_documentation_mentions_product_boundary(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("does not", content)
        self.assertIn("create final Meal records", content)
        self.assertIn("modify existing DailyPlans", content)
        self.assertIn("apply proposals", content)

    def test_documentation_mentions_next_stage(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("Etapa 3", content)
        self.assertIn("Crear propuesta de DailyPlan desde MCP", content)
