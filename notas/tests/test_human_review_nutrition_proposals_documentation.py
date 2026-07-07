from pathlib import Path

from django.test import SimpleTestCase


class HumanReviewNutritionProposalsDocumentationTests(SimpleTestCase):
    DOC_PATH = Path("docs/archive/legacy_context/human_review_nutrition_proposals.md")

    def test_documentation_exists(self):
        self.assertTrue(self.DOC_PATH.exists())

    def test_documentation_mentions_supported_intents(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("create_meal", content)
        self.assertIn("create_dailyplan", content)

    def test_documentation_mentions_review_viewmodel(self):
        content = self.DOC_PATH.read_text()

        self.assertIn(
            "notas/presentation/proposals/proposal_review_viewmodels.py",
            content,
        )
        self.assertIn("build_proposal_review_vm", content)
        self.assertIn("vm.content.proposal_review", content)

    def test_documentation_mentions_templates(self):
        content = self.DOC_PATH.read_text()

        self.assertIn(
            "notas/templates/notas/proposals/partials/review_create_meal.html",
            content,
        )
        self.assertIn(
            "notas/templates/notas/proposals/partials/review_create_dailyplan.html",
            content,
        )
        self.assertIn(
            "notas/templates/notas/proposals/partials/review_actions.html",
            content,
        )

    def test_documentation_mentions_safe_boundary(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("does not apply nutrition changes", content)
        self.assertIn("does not create a final `Meal`", content)
        self.assertIn("does not create a final `DailyPlan`", content)

    def test_documentation_mentions_review_actions(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("Aprobar propuesta", content)
        self.assertIn("Rechazar propuesta", content)
        self.assertIn("Cancelar propuesta", content)

    def test_documentation_mentions_next_stage(self):
        content = self.DOC_PATH.read_text()

        self.assertIn("Etapa 5", content)
        self.assertIn("Safe Apply Flow for Approved Proposals", content)
