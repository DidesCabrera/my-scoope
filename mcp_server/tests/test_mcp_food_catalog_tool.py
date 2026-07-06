import unittest

from myscoope_mcp.contracts import MCPToolCallResult
from myscoope_mcp.dispatcher import dispatch_tool_call
from myscoope_mcp.tool_handlers import (
    call_read_tool,
    list_food_catalog,
)
from myscoope_mcp.tools import TOOL_LIST_FOOD_CATALOG, get_tool_spec


class FakeMyscoopeAPIClient:
    def __init__(self):
        self.calls = []

    def call_ai_tool_api(self, api_path, payload):
        self.calls.append(
            {
                "api_path": api_path,
                "payload": payload,
            }
        )

        return MCPToolCallResult(
            ok=True,
            data={
                "api_path": api_path,
                "payload": payload,
            },
            error=None,
        )


class MCPFoodCatalogToolTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeMyscoopeAPIClient()

    def test_list_food_catalog_calls_api_adapter(self):
        result = list_food_catalog(
            self.client,
            search="pollo",
            limit=25,
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            self.client.calls,
            [
                {
                    "api_path": "/ai-tools/list-food-catalog/",
                    "payload": {
                        "limit": 25,
                        "search": "pollo",
                    },
                }
            ],
        )

    def test_call_read_tool_dispatches_list_food_catalog(self):
        result = call_read_tool(
            self.client,
            TOOL_LIST_FOOD_CATALOG,
            {
                "search": "arroz",
                "limit": 10,
            },
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            self.client.calls,
            [
                {
                    "api_path": "/ai-tools/list-food-catalog/",
                    "payload": {
                        "limit": 10,
                        "search": "arroz",
                    },
                }
            ],
        )

    def test_list_food_catalog_does_not_forward_catalog_trace_arguments(self):
        result = call_read_tool(
            self.client,
            TOOL_LIST_FOOD_CATALOG,
            {
                "search": "pollo",
                "limit": 10,
                "catalog_food_id": 999,
                "catalog_food_ref": "cat:999",
            },
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            self.client.calls,
            [
                {
                    "api_path": "/ai-tools/list-food-catalog/",
                    "payload": {
                        "limit": 10,
                        "search": "pollo",
                    },
                }
            ],
        )

    def test_list_food_catalog_spec_documents_operational_food_ids_only(self):
        spec = get_tool_spec(TOOL_LIST_FOOD_CATALOG)

        self.assertIn("operational foods", spec.description)
        self.assertIn("operational My Scoope Food IDs", spec.description)
        self.assertNotIn("catalog_food_id", str(spec.input_schema))
        self.assertNotIn("catalog_food_ref", str(spec.input_schema))

    def test_dispatch_tool_call_routes_list_food_catalog(self):
        result = dispatch_tool_call(
            client=self.client,
            tool_name=TOOL_LIST_FOOD_CATALOG,
            arguments={
                "search": "banana",
                "limit": 5,
            },
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            self.client.calls,
            [
                {
                    "api_path": "/ai-tools/list-food-catalog/",
                    "payload": {
                        "limit": 5,
                        "search": "banana",
                    },
                }
            ],
        )

if __name__ == "__main__":
    unittest.main()
