import unittest

from ai_assistant.application.tools.registry import list_mcp_tool_specs
from myscoope_mcp.tools import list_allowed_tool_specs


class MCPCanonicalCatalogAdapterTests(unittest.TestCase):
    def test_mcp_specs_are_a_projection_of_the_canonical_catalog(self):
        canonical = {
            spec.mcp_name: (
                spec.description,
                spec.mcp_api_path,
                dict(spec.mcp_input_schema or spec.input_schema),
            )
            for spec in list_mcp_tool_specs()
        }
        adapted = {
            spec.name: (
                spec.description,
                spec.api_path,
                dict(spec.input_schema),
            )
            for spec in list_allowed_tool_specs()
        }

        self.assertEqual(adapted, canonical)
