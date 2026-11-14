import asyncio
import unittest
from unittest.mock import patch

from myscoope_mcp.contracts import MCPToolCallResult
from myscoope_mcp.protocol_server import (
    DAILYPLAN_CARD_RESOURCE_URI,
    FOOD_CARD_RESOURCE_URI,
    MEAL_CARD_MIME_TYPE,
    create_mcp_server,
)


class FakeAPIClient:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def call_ai_tool_api(self, api_path, payload):
        self.calls.append((api_path, payload))
        return self.result


class MCPEntityCardTests(unittest.TestCase):
    def test_read_tools_link_to_registered_card_resources(self):
        async def inspect():
            server = create_mcp_server()
            tools = {tool.name: tool for tool in await server.list_tools()}
            resources = {str(resource.uri): resource for resource in await server.list_resources()}
            contents = [await server.read_resource(uri) for uri in (FOOD_CARD_RESOURCE_URI, DAILYPLAN_CARD_RESOURCE_URI)]
            return tools, resources, contents

        tools, resources, contents = asyncio.run(inspect())
        for name, uri in (("read_food", FOOD_CARD_RESOURCE_URI), ("read_dailyplan", DAILYPLAN_CARD_RESOURCE_URI)):
            self.assertEqual(tools[name].meta["ui"]["resourceUri"], uri)
            self.assertEqual(resources[uri].mimeType, MEAL_CARD_MIME_TYPE)
            self.assertTrue(tools[name].annotations.readOnlyHint)
            self.assertEqual(tools[name].securitySchemes, [{"type": "oauth2", "scopes": ["myscoope:read"]}])
            self.assertEqual(set(tools[name].outputSchema["required"]), {"ok", "data", "error"})
        self.assertIn('id="entity-name"', contents[0][0].content)
        self.assertIn('id="detail-panel"', contents[1][0].content)
        self.assertIn('method: "ui/initialize"', contents[0][0].content)

    def test_read_food_uses_authorized_api_and_preserves_result(self):
        food = {"id": 12, "name": "Avena", "macros": {"total_kcal": 382}}
        client = FakeAPIClient(MCPToolCallResult(ok=True, data={"food": food}, error=None))

        async def call():
            with patch("myscoope_mcp.protocol_server.create_api_client", return_value=client):
                return await create_mcp_server().call_tool("read_food", {"food_id": 12})

        _, structured = asyncio.run(call())
        self.assertEqual(client.calls, [("/ai-tools/read-food/", {"food_id": 12})])
        self.assertEqual(structured["data"]["food"], food)

    def test_denial_contains_no_entity_data(self):
        client = FakeAPIClient(MCPToolCallResult(ok=False, data={}, error={"code": "not_found"}))

        async def call():
            with patch("myscoope_mcp.protocol_server.create_api_client", return_value=client):
                return await create_mcp_server().call_tool("read_food", {"food_id": 12})

        _, structured = asyncio.run(call())
        self.assertFalse(structured["ok"])
        self.assertEqual(structured["data"], {})
