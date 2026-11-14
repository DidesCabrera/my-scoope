import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from mcp.server.auth.provider import AccessToken
from myscoope_mcp.auth import StaticMCPTokenVerifier, create_external_mcp_auth_settings
from myscoope_mcp.contracts import MCPToolCallResult
from myscoope_mcp.protocol_server import (
    MEAL_CARD_MIME_TYPE,
    MEAL_CARD_RESOURCE_URI,
    create_mcp_server,
)
from myscoope_mcp.run_protocol_server import _create_http_app


class FakeAPIClient:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def call_ai_tool_api(self, api_path, payload):
        self.calls.append((api_path, payload))
        return self.result


class MCPMealCardUITests(unittest.TestCase):
    def test_read_meal_links_to_a_registered_html_resource(self):
        async def inspect():
            server = create_mcp_server()
            tools = {tool.name: tool for tool in await server.list_tools()}
            resources = {str(resource.uri): resource for resource in await server.list_resources()}
            contents = await server.read_resource(MEAL_CARD_RESOURCE_URI)
            return tools, resources[MEAL_CARD_RESOURCE_URI], contents[0]

        tools, resource, content = asyncio.run(inspect())
        tool = tools["read_meal"]
        self.assertEqual(tool.meta["ui"]["resourceUri"], MEAL_CARD_RESOURCE_URI)
        self.assertIsNone(tools["search_user_meals"].meta)
        self.assertEqual(tools["search_user_meals"].inputSchema["properties"]["limit"]["maximum"], 10)
        self.assertEqual(set(tool.outputSchema["required"]), {"ok", "data", "error"})
        self.assertTrue(tool.annotations.readOnlyHint)
        self.assertEqual(tool.securitySchemes, [{"type": "oauth2", "scopes": ["myscoope:read"]}])
        self.assertNotIn("user_id", tool.inputSchema.get("properties", {}))
        self.assertEqual(resource.mimeType, MEAL_CARD_MIME_TYPE)
        self.assertEqual(content.mime_type, MEAL_CARD_MIME_TYPE)
        self.assertIn("ui/notifications/tool-result", content.content)

    def test_read_meal_delivers_the_authorized_result_as_structured_content(self):
        meal = {
            "id": 23, "name": "Almuerzo", "kpis": {"total_kcal": 500}, "foods": [],
        }
        client = FakeAPIClient(MCPToolCallResult(ok=True, data={"meal": meal}, error=None))

        async def call():
            with patch("myscoope_mcp.protocol_server.create_api_client", return_value=client):
                return await create_mcp_server().call_tool("read_meal", {"meal_id": 23})

        _, structured = asyncio.run(call())
        self.assertEqual(client.calls, [('/ai-tools/read-meal/', {"meal_id": 23})])
        self.assertEqual(structured["data"]["meal"], meal)

    def test_api_denial_is_preserved_and_contains_no_meal(self):
        client = FakeAPIClient(MCPToolCallResult(
            ok=False, data={}, error={"code": "not_found", "message": "Not found.", "details": {}},
        ))

        async def call():
            with patch("myscoope_mcp.protocol_server.create_api_client", return_value=client):
                return await create_mcp_server().call_tool("read_meal", {"meal_id": 23})

        _, structured = asyncio.run(call())
        self.assertFalse(structured["ok"])
        self.assertNotIn("meal", structured["data"])


class MCPMealCardHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def test_authenticated_http_lists_and_serves_card_and_meal(self):
        origin = "http://127.0.0.1:8001"
        verifier = StaticMCPTokenVerifier(expected_token="", resource=origin)
        server = create_mcp_server(
            token_verifier=verifier,
            auth_settings=create_external_mcp_auth_settings(origin),
        )
        app = _create_http_app(server)
        api_client = FakeAPIClient(MCPToolCallResult(
            ok=True,
            data={"meal": {"id": 23, "name": "Almuerzo", "kpis": {}, "foods": []}},
            error=None,
        ))
        access_token = AccessToken(
            token="mcp_user_verified", client_id="test", scopes=["myscoope:read"], resource=origin,
        )
        with patch.object(verifier, "_introspect_user_token", new_callable=AsyncMock) as introspect, patch(
            "myscoope_mcp.protocol_server.create_api_client", return_value=api_client,
        ):
            introspect.return_value = access_token
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url=origin,
                    headers={
                        "Authorization": "Bearer mcp_user_verified",
                        "Accept": "application/json, text/event-stream",
                    },
                ) as client:
                    async def rpc(method, params, request_id):
                        response = await client.post("/mcp", json={
                            "jsonrpc": "2.0", "id": request_id, "method": method, "params": params,
                        })
                        self.assertEqual(response.status_code, 200, response.text)
                        return response.json()["result"]

                    listed = await rpc("tools/list", {}, 1)
                    meal_tool = next(tool for tool in listed["tools"] if tool["name"] == "read_meal")
                    self.assertEqual(meal_tool["_meta"]["ui"]["resourceUri"], MEAL_CARD_RESOURCE_URI)
                    resource = await rpc("resources/read", {"uri": MEAL_CARD_RESOURCE_URI}, 2)
                    self.assertEqual(resource["contents"][0]["mimeType"], MEAL_CARD_MIME_TYPE)
                    self.assertIn("ui/notifications/tool-result", resource["contents"][0]["text"])
                    called = await rpc("tools/call", {"name": "read_meal", "arguments": {"meal_id": 23}}, 3)
                    self.assertEqual(called["structuredContent"]["data"]["meal"]["id"], 23)
        self.assertEqual(api_client.calls, [("/ai-tools/read-meal/", {"meal_id": 23})])


if __name__ == "__main__":
    unittest.main()
