from pathlib import Path
import unittest


AUTH_DOC_PATH = Path("docs/archive/mcp_stage_logs/internal_api_auth_for_mcp.md")
ENV_DOC_PATH = Path("docs/archive/mcp_stage_logs/mcp_local_env_setup.md")


class MCPLocalEnvSetupDocumentationTests(unittest.TestCase):
    def test_internal_auth_doc_exists(self):
        self.assertTrue(
            AUTH_DOC_PATH.exists(),
            msg="Internal API auth documentation should exist.",
        )

    def test_local_env_doc_exists(self):
        self.assertTrue(
            ENV_DOC_PATH.exists(),
            msg="MCP local environment setup documentation should exist.",
        )

    def test_internal_auth_doc_documents_django_env_vars(self):
        text = AUTH_DOC_PATH.read_text()

        self.assertIn("MYSCOOPE_INTERNAL_API_TOKEN", text)
        self.assertIn("MYSCOOPE_INTERNAL_API_USERNAME", text)

    def test_internal_auth_doc_documents_mcp_env_vars(self):
        text = AUTH_DOC_PATH.read_text()

        self.assertIn("MYSCOOPE_API_BASE_URL", text)
        self.assertIn("MYSCOOPE_API_AUTH_TOKEN", text)

    def test_internal_auth_doc_documents_bearer_flow(self):
        text = AUTH_DOC_PATH.read_text()

        self.assertIn("Authorization: Bearer", text)
        self.assertIn("request.user", text)

    def test_internal_auth_doc_rejects_payload_user_id_authority(self):
        text = AUTH_DOC_PATH.read_text()

        self.assertIn("must not accept user_id", text)
        self.assertIn("impersonating another user", text)

    def test_local_env_doc_documents_inspector_command(self):
        text = ENV_DOC_PATH.read_text()

        self.assertIn("/Users/felipedides/Desktop/proyecto_django/venv/bin/python", text)
        self.assertIn("-m myscoope_mcp.run_protocol_server", text)

    def test_local_env_doc_documents_no_check_in_inspector(self):
        text = ENV_DOC_PATH.read_text()

        self.assertIn("Do not use --check in Inspector.", text)

    def test_local_env_doc_documents_real_flow(self):
        text = ENV_DOC_PATH.read_text()

        self.assertIn("MCP Inspector", text)
        self.assertIn("FastMCP server", text)
        self.assertIn("Django API Adapter", text)
        self.assertIn("request.user = felipe", text)

    def test_local_env_doc_documents_security_note(self):
        text = ENV_DOC_PATH.read_text()

        self.assertIn("Do not expose dev-mcp-token publicly.", text)
        self.assertIn("per-user revocable tokens", text)


if __name__ == "__main__":
    unittest.main()
