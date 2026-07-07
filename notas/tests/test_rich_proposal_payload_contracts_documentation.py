from pathlib import Path

from django.test import SimpleTestCase


class RichProposalPayloadContractsDocumentationTests(SimpleTestCase):
    DOC_PATH = Path("docs/archive/legacy_context/rich_proposal_payload_contracts.md")

    def test_documentation_exists(self):
        self.assertTrue(self.DOC_PATH.exists())

    def test_documentation_mentions_supported_intents(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("create_meal", content)
        self.assertIn("create_dailyplan", content)

    def test_documentation_mentions_core_modules(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("notas/application/dto/proposal_payloads.py", content)
        self.assertIn(
            "notas/application/validation/proposal_payload_validators.py",
            content,
        )
        self.assertIn(
            "notas/application/queries/proposal_simulation_queries.py",
            content,
        )

    def test_documentation_mentions_product_boundary(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("does not", content)
        self.assertIn("create Meal records", content)
        self.assertIn("modify existing DailyPlans", content)
        self.assertIn("apply proposals", content)

    def test_documentation_mentions_next_stage(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("Etapa 2", content)
        self.assertIn("Crear propuesta de comida desde MCP", content)
