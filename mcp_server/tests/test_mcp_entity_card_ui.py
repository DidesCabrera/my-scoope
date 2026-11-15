import asyncio
import unittest
from unittest.mock import patch

from myscoope_mcp.contracts import MCPToolCallResult
from myscoope_mcp.protocol_server import (
    DAILYPLAN_CARD_RESOURCE_URI,
    FOOD_CARD_RESOURCE_URI,
    MEAL_CARD_MIME_TYPE,
    PREVIOUS_DAILYPLAN_CARD_RESOURCE_URI,
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
            with patch.dict("os.environ", {
                "MYSCOOPE_API_BASE_URL": "http://127.0.0.1:8000/app",
                "MYSCOOPE_CARD_WEB_APP_BASE_URL": "",
            }):
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
        self.assertIn('id="menu-tab"', contents[1][0].content)
        self.assertIn('id="nutrition-tab"', contents[1][0].content)
        self.assertIn('id="nutrition-panel"', contents[1][0].content)
        self.assertIn('id="detail-link"', contents[1][0].content)
        self.assertIn('"http://127.0.0.1:8000/app"', contents[1][0].content)
        self.assertEqual(contents[1][0].meta["openai/widgetCSP"]["redirect_domains"], ["http://127.0.0.1:8000"])
        self.assertIn(PREVIOUS_DAILYPLAN_CARD_RESOURCE_URI, resources)
        for tab in ("calories", "macros", "dist", "alloc"):
            self.assertIn(f'id="{tab}-tab"', contents[1][0].content)
            self.assertIn(f'id="{tab}-panel"', contents[1][0].content)
        self.assertIn('method: "ui/initialize"', contents[0][0].content)

    def test_dailyplan_link_uses_configured_web_origin(self):
        async def inspect():
            with patch.dict("os.environ", {
                "MYSCOOPE_API_BASE_URL": "https://internal.example.test/app",
                "MYSCOOPE_CARD_WEB_APP_BASE_URL": "https://myscoope-staging.onrender.com/app",
            }):
                server = create_mcp_server()
                return (await server.read_resource(DAILYPLAN_CARD_RESOURCE_URI))[0]

        resource = asyncio.run(inspect())
        self.assertIn('"https://myscoope-staging.onrender.com/app"', resource.content)
        self.assertEqual(resource.meta["openai/widgetCSP"]["redirect_domains"], ["https://myscoope-staging.onrender.com"])

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
