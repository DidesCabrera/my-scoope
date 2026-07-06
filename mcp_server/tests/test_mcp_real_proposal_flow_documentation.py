from pathlib import Path
import unittest


DOC_PATH = Path("docs/archive/mcp_stage_logs/mcp_real_proposal_flow_test.md")


class MCPRealProposalFlowDocumentationTests(unittest.TestCase):
    def test_doc_exists(self):
        self.assertTrue(
            DOC_PATH.exists(),
            msg="MCP real proposal flow documentation should exist.",
        )

    def test_doc_documents_required_tools(self):
        text = DOC_PATH.read_text()

        self.assertIn("read_dailyplan", text)
        self.assertIn("compare_dailyplan_to_targets", text)
        self.assertIn("create_validated_dailyplan_proposal", text)

    def test_doc_documents_proposal_verification(self):
        text = DOC_PATH.read_text()

        self.assertIn("/app/proposals/", text)
        self.assertIn("Propuesta MCP - Ajuste de proteína", text)

    def test_doc_documents_product_boundary(self):
        text = DOC_PATH.read_text()

        self.assertIn("does not", text)
        self.assertIn("approve the proposal", text)
        self.assertIn("apply the proposal", text)
        self.assertIn("modify the final DailyPlan", text)

    def test_doc_documents_auth_boundary(self):
        text = DOC_PATH.read_text()

        self.assertIn("Internal API Auth for MCP", text)
        self.assertIn("authentication-related error", text)


if __name__ == "__main__":
    unittest.main()
