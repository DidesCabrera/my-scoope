from pathlib import Path
import unittest


DOC_PATH = Path("docs/archive/mcp_stage_logs/mcp_list_user_proposals_test.md")


class MCPListUserProposalsDocumentationTests(unittest.TestCase):
    def test_doc_exists(self):
        self.assertTrue(
            DOC_PATH.exists(),
            msg="MCP list_user_proposals test documentation should exist.",
        )

    def test_doc_documents_tool_name(self):
        text = DOC_PATH.read_text()

        self.assertIn("list_user_proposals", text)

    def test_doc_documents_inspector_configuration(self):
        text = DOC_PATH.read_text()

        self.assertIn("STDIO", text)
        self.assertIn("myscoope_mcp.run_protocol_server", text)
        self.assertIn("PYTHONPATH=mcp_server", text)

    def test_doc_documents_success_contract(self):
        text = DOC_PATH.read_text()

        self.assertIn('"ok": true', text)
        self.assertIn('"proposals": []', text)
        self.assertIn('"error": null', text)

    def test_doc_documents_auth_boundary(self):
        text = DOC_PATH.read_text()

        self.assertIn("Internal API Auth for MCP", text)
        self.assertIn("authentication-related", text)


if __name__ == "__main__":
    unittest.main()
