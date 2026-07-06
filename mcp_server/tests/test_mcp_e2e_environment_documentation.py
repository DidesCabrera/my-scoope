from pathlib import Path
import unittest


DOC_PATH = Path("docs/archive/mcp_stage_logs/mcp_e2e_environment_preparation.md")


class MCPE2EEnvironmentDocumentationTests(unittest.TestCase):
    def test_doc_exists(self):
        self.assertTrue(
            DOC_PATH.exists(),
            msg="MCP E2E environment preparation documentation should exist.",
        )

    def test_doc_documents_django_env_vars(self):
        text = DOC_PATH.read_text()

        self.assertIn("MYSCOOPE_INTERNAL_API_TOKEN", text)
        self.assertIn("MYSCOOPE_INTERNAL_API_USERNAME", text)

    def test_doc_documents_mcp_inspector_env_vars(self):
        text = DOC_PATH.read_text()

        self.assertIn("MYSCOOPE_API_BASE_URL", text)
        self.assertIn("MYSCOOPE_API_AUTH_TOKEN", text)
        self.assertIn("PYTHONPATH=mcp_server", text)

    def test_doc_documents_token_matching_rule(self):
        text = DOC_PATH.read_text()

        self.assertIn("Token Matching Rule", text)
        self.assertIn("must match", text)

    def test_doc_documents_product_boundary(self):
        text = DOC_PATH.read_text()

        self.assertIn("create proposals", text)
        self.assertIn("approve proposals", text)
        self.assertIn("apply proposals", text)
        self.assertIn("bypass human review", text)


if __name__ == "__main__":
    unittest.main()
