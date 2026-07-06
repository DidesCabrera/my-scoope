from pathlib import Path
import unittest


DOC_PATH = Path("docs/archive/mcp_stage_logs/internal_api_auth_for_mcp.md")


class InternalAPIAuthDocumentationTests(unittest.TestCase):
    def test_doc_exists(self):
        self.assertTrue(
            DOC_PATH.exists(),
            msg="Internal API Auth for MCP documentation should exist.",
        )

    def test_doc_documents_required_environment_variables(self):
        text = DOC_PATH.read_text()

        self.assertIn("MYSCOOPE_INTERNAL_API_TOKEN", text)
        self.assertIn("MYSCOOPE_INTERNAL_API_USERNAME", text)

    def test_doc_documents_bearer_auth(self):
        text = DOC_PATH.read_text()

        self.assertIn("Authorization: Bearer", text)

    def test_doc_rejects_payload_user_id_authority(self):
        text = DOC_PATH.read_text()

        self.assertIn("must not accept user_id", text)
        self.assertIn("prevents an external client from impersonating another user", text)

    def test_doc_preserves_session_auth(self):
        text = DOC_PATH.read_text()

        self.assertIn("Session Auth Still Works", text)
        self.assertIn("Browser session user", text)

    def test_doc_preserves_product_boundary(self):
        text = DOC_PATH.read_text()

        self.assertIn("MCP can read.", text)
        self.assertIn("MCP can validate.", text)
        self.assertIn("MCP can create proposals.", text)
        self.assertIn("MCP must not apply final changes directly.", text)


if __name__ == "__main__":
    unittest.main()
