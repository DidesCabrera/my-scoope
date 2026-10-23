import time
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from mcp.server.auth.provider import AccessToken
from myscoope_mcp.auth import (
    StaticMCPTokenVerifier,
    create_external_mcp_auth_settings,
    create_external_mcp_token_verifier,
    get_external_mcp_auth_token,
    get_mcp_public_url,
)


class MCPExternalAuthTests(unittest.IsolatedAsyncioTestCase):
    @patch.dict(
        "os.environ",
        {},
        clear=True,
    )
    def test_external_token_returns_none_when_missing(self):
        self.assertIsNone(
            get_external_mcp_auth_token(),
        )

    @patch.dict(
        "os.environ",
        {
            "MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN": "  external-token  ",
        },
        clear=True,
    )
    def test_external_token_is_trimmed(self):
        self.assertEqual(
            get_external_mcp_auth_token(),
            "external-token",
        )

    async def test_static_verifier_accepts_matching_token(self):
        verifier = StaticMCPTokenVerifier(
            expected_token="external-token",
            resource="http://127.0.0.1:8001",
        )

        access_token = await verifier.verify_token("external-token")

        self.assertIsNotNone(access_token)
        self.assertEqual(
            access_token.client_id,
            "myscoope-external-mcp-client",
        )
        self.assertEqual(
            access_token.scopes,
            [
                "myscoope:read",
                "myscoope:proposals:create",
            ],
        )
        self.assertEqual(
            access_token.resource,
            "http://127.0.0.1:8001",
        )

    async def test_static_verifier_rejects_wrong_token(self):
        verifier = StaticMCPTokenVerifier(
            expected_token="external-token",
            resource="http://127.0.0.1:8001",
        )

        access_token = await verifier.verify_token("wrong-token")

        self.assertIsNone(access_token)

    @patch.dict(
        "os.environ",
        {},
        clear=True,
    )
    def test_public_url_defaults_to_host_and_port(self):
        self.assertEqual(
            get_mcp_public_url(
                host="127.0.0.1",
                port=8001,
            ),
            "http://127.0.0.1:8001",
        )

    @patch.dict(
        "os.environ",
        {
            "MYSCOOPE_MCP_PUBLIC_URL": "https://mcp.myscoope.com/",
        },
        clear=True,
    )
    def test_public_url_reads_env_and_strips_trailing_slash(self):
        self.assertEqual(
            get_mcp_public_url(
                host="0.0.0.0",
                port=10000,
            ),
            "https://mcp.myscoope.com",
        )

    @patch.dict(
        "os.environ",
        {},
        clear=True,
    )
    def test_auth_settings_use_public_url_by_default(self):
        auth_settings = create_external_mcp_auth_settings(
            public_url="http://127.0.0.1:8001",
        )

        self.assertEqual(
            str(auth_settings.resource_server_url).rstrip("/"),
            "http://127.0.0.1:8001",
        )

    @patch.dict(
        "os.environ",
        {
            "MYSCOOPE_MCP_EXTERNAL_AUTH_TOKEN": "external-token",
        },
        clear=True,
    )
    def test_create_token_verifier_requires_env_token(self):
        verifier = create_external_mcp_token_verifier(
            public_url="http://127.0.0.1:8001",
        )

        self.assertIsInstance(
            verifier,
            StaticMCPTokenVerifier,
        )

    @patch.dict(
        "os.environ",
        {},
        clear=True,
    )
    def test_create_token_verifier_fails_without_env_token(self):
        with self.assertRaises(RuntimeError):
            create_external_mcp_token_verifier(
                public_url="http://127.0.0.1:8001",
            )

    @patch.dict(
        "os.environ",
        {"MYSCOOPE_MCP_USER_TOKENS_ONLY": "true"},
        clear=True,
    )
    async def test_user_only_mode_needs_no_static_secret_and_rejects_it(self):
        verifier = create_external_mcp_token_verifier(
            public_url="http://127.0.0.1:8001",
        )
        self.assertIsNone(await verifier.verify_token("external-token"))
        self.assertIsNone(await verifier.verify_token("mcp_user_example-token"))


    @patch.dict("os.environ", {"MYSCOOPE_API_BASE_URL": "https://api.example.test/app"})
    async def test_user_token_uses_verified_scopes_and_resource(self):
        seen = []

        def responder(request):
            seen.append(request)
            return httpx.Response(200, json={
                "active": True,
                "scopes": ["myscoope:read"],
                "resource": "https://mcp.example.test",
                "expires_at": int(time.time()) + 60,
            })

        client = httpx.AsyncClient(transport=httpx.MockTransport(responder))
        verifier = StaticMCPTokenVerifier(
            expected_token="",
            resource="https://mcp.example.test",
        )
        with patch("myscoope_mcp.auth.httpx.AsyncClient", return_value=client):
            access_token = await verifier.verify_token("mcp_user_real-token")

        self.assertIsNotNone(access_token)
        self.assertEqual(access_token.scopes, ["myscoope:read"])
        self.assertEqual(seen[0].url.path, "/app/ai-tools/mcp-token-introspection/")
        self.assertEqual(seen[0].headers["authorization"], "Bearer mcp_user_real-token")

    @patch.dict("os.environ", {"MYSCOOPE_API_BASE_URL": "https://api.example.test/app"})
    async def test_user_token_rejects_wrong_resource_and_inactive_response(self):
        for status, payload in [
            (401, {"active": False}),
            (200, {"active": True, "scopes": ["myscoope:read"],
                   "resource": "https://other.example.test", "expires_at": int(time.time()) + 60}),
        ]:
            client = httpx.AsyncClient(
                transport=httpx.MockTransport(lambda request: httpx.Response(status, json=payload))
            )
            verifier = StaticMCPTokenVerifier(expected_token="", resource="https://mcp.example.test")
            with patch("myscoope_mcp.auth.httpx.AsyncClient", return_value=client):
                self.assertIsNone(await verifier.verify_token("mcp_user_fake"))

    @patch.object(StaticMCPTokenVerifier, "_introspect_user_token", new_callable=AsyncMock)
    async def test_static_verifier_accepts_mcp_user_token_when_enabled(self, introspect):
        verifier = StaticMCPTokenVerifier(
            expected_token="external-token",
            resource="http://127.0.0.1:8001",
        )
        introspect.return_value = AccessToken(
            token="mcp_user_example-token",
            client_id="myscoope-mcp-user-token-client",
            scopes=["myscoope:read"],
            resource="http://127.0.0.1:8001",
        )

        access_token = await verifier.verify_token(
            "mcp_user_example-token",
        )

        self.assertIsNotNone(access_token)
        self.assertEqual(
            access_token.token,
            "mcp_user_example-token",
        )
        self.assertEqual(
            access_token.client_id,
            "myscoope-mcp-user-token-client",
        )
        self.assertEqual(
            access_token.scopes,
            [
                "myscoope:read",
            ],
        )
        self.assertEqual(
            access_token.resource,
            "http://127.0.0.1:8001",
        )

    async def test_static_verifier_can_disable_mcp_user_tokens(self):
        verifier = StaticMCPTokenVerifier(
            expected_token="external-token",
            resource="http://127.0.0.1:8001",
            allow_mcp_user_tokens=False,
        )

        access_token = await verifier.verify_token(
            "mcp_user_example-token",
        )

        self.assertIsNone(access_token)

        
if __name__ == "__main__":
    unittest.main()
