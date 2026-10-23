import unittest
from unittest.mock import AsyncMock, patch

import httpx
from mcp.server.auth.provider import AccessToken
from myscoope_mcp.auth import StaticMCPTokenVerifier, create_external_mcp_auth_settings
from myscoope_mcp.protocol_server import create_mcp_server
from myscoope_mcp.run_protocol_server import _create_http_app


class MCPHTTPAuthBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_fake_token_cannot_initialize_or_list_tools(self):
        resource = "http://127.0.0.1:8001"
        verifier = StaticMCPTokenVerifier(expected_token="", resource=resource)
        server = create_mcp_server(
            token_verifier=verifier,
            auth_settings=create_external_mcp_auth_settings(resource),
        )
        app = _create_http_app(server)
        with patch.object(verifier, "_introspect_user_token", new_callable=AsyncMock) as introspect:
            introspect.return_value = None
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url=resource,
                    headers={
                        "Authorization": "Bearer mcp_user_invented",
                        "Accept": "application/json, text/event-stream",
                    },
                ) as client:
                    for method, params in [
                        ("initialize", {
                            "protocolVersion": "2025-11-25",
                            "capabilities": {},
                            "clientInfo": {"name": "security-test", "version": "1"},
                        }),
                        ("tools/list", {}),
                    ]:
                        response = await client.post(
                            "/mcp",
                            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                        )
                        self.assertEqual(response.status_code, 401, method)
            self.assertEqual(introspect.await_count, 2)

    async def test_verified_read_only_token_can_initialize_without_write_scope(self):
        resource = "http://127.0.0.1:8001"
        verifier = StaticMCPTokenVerifier(expected_token="", resource=resource)
        server = create_mcp_server(
            token_verifier=verifier,
            auth_settings=create_external_mcp_auth_settings(resource),
        )
        app = _create_http_app(server)
        with patch.object(verifier, "_introspect_user_token", new_callable=AsyncMock) as introspect:
            introspect.return_value = AccessToken(
                token="mcp_user_verified",
                client_id="test",
                scopes=["myscoope:read"],
                resource=resource,
            )
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url=resource,
                    headers={
                        "Authorization": "Bearer mcp_user_verified",
                        "Accept": "application/json, text/event-stream",
                    },
                ) as client:
                    response = await client.post(
                        "/mcp",
                        json={
                            "jsonrpc": "2.0", "id": 1, "method": "initialize",
                            "params": {
                                "protocolVersion": "2025-11-25",
                                "capabilities": {},
                                "clientInfo": {"name": "security-test", "version": "1"},
                            },
                        },
                    )
                    self.assertEqual(response.status_code, 200)
                    listed = await client.post(
                        "/mcp",
                        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                    )
                    self.assertEqual(listed.status_code, 200)
                    self.assertIn("list_food_catalog", listed.text)
                    self.assertIn("securitySchemes", listed.text)
