from pathlib import Path
import unittest


INSPECTOR_DOC_PATH = Path(
    "docs/archive/mcp_stage_logs/mcp_inspector_connection.md"
)


class MCPInspectorDocumentationTests(unittest.TestCase):
    def test_inspector_doc_exists(self):
        self.assertTrue(
            INSPECTOR_DOC_PATH.exists(),
            msg="MCP Inspector connection documentation should exist.",
        )

    def test_inspector_doc_documents_stdio_configuration(self):
        text = INSPECTOR_DOC_PATH.read_text()

        self.assertIn("Transport Type: STDIO", text)
        self.assertIn("myscoope_mcp.run_protocol_server", text)
        self.assertIn("PYTHONPATH=mcp_server", text)

    def test_inspector_doc_documents_expected_tools(self):
        text = INSPECTOR_DOC_PATH.read_text()

        self.assertIn("list_user_proposals", text)
        self.assertIn("read_dailyplan", text)
        self.assertIn("read_proposal", text)
        self.assertIn("compare_dailyplan_to_targets", text)
        self.assertIn("create_validated_dailyplan_proposal", text)

    def test_inspector_doc_warns_not_to_use_check_mode_in_inspector(self):
        text = INSPECTOR_DOC_PATH.read_text()

        self.assertIn("Do not use `--check` in Inspector.", text)