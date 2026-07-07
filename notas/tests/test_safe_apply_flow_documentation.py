from pathlib import Path

from django.test import SimpleTestCase


class SafeApplyFlowDocumentationTests(SimpleTestCase):
    DOC_PATH = Path("docs/archive/legacy_context/safe_apply_flow_for_approved_proposals.md")

    def test_documentation_exists(self):
        self.assertTrue(self.DOC_PATH.exists())

    def test_documentation_mentions_supported_intents(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("create_meal", content)
        self.assertIn("create_dailyplan", content)

    def test_documentation_mentions_apply_contract_layer(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("notas/application/dto/proposal_apply.py", content)
        self.assertIn("build_create_meal_apply_plan", content)
        self.assertIn("build_create_dailyplan_apply_plan", content)

    def test_documentation_mentions_apply_commands(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("apply_approved_create_meal_proposal", content)
        self.assertIn("apply_approved_create_dailyplan_proposal", content)

    def test_documentation_mentions_create_meal_boundary(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("does not", content)
        self.assertIn("attach the Meal to any DailyPlan", content)
        self.assertIn("modify the context DailyPlan", content)

    def test_documentation_mentions_create_dailyplan_snapshots(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("snapshot Meals", content)
        self.assertIn("DailyPlanMeal", content)
        self.assertIn("not reusable Meals", content)

    def test_documentation_mentions_mcp_boundary(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("Apply tools are not exposed to MCP", content)
        self.assertIn("MCP cannot", content)
        self.assertIn("apply", content)

    def test_documentation_mentions_next_stage(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("Etapa 6", content)
        self.assertIn("Apply UI Integration", content)
