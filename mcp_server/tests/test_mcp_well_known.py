import json
import unittest
from unittest.mock import patch

from myscoope_mcp.well_known import (
    get_mcp_resource_url,
    get_oauth_issuer_url,
    get_protected_resource_scopes,
    oauth_protected_resource_metadata,
    openai_apps_challenge,
)


class MCPWellKnownTests(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {},
        clear=True,
    )
    def test_resource_url_defaults_to_render_mcp_origin(self):
        self.assertEqual(
            get_mcp_resource_url(),
            "https://myscoope-mcp.onrender.com",
        )

    @patch.dict(
        "os.environ",
        {
            "MYSCOOPE_MCP_RESOURCE_URL": "https://mcp.example.com/",
        },
        clear=True,
    )
    def test_resource_url_reads_env_and_strips_trailing_slash(self):
        self.assertEqual(
            get_mcp_resource_url(),
            "https://mcp.example.com",
        )

    @patch.dict(
        "os.environ",
        {},
        clear=True,
    )
    def test_oauth_issuer_url_defaults_to_myscoope(self):
        self.assertEqual(
            get_oauth_issuer_url(),
            "https://www.myscoope.com",
        )

    @patch.dict(
        "os.environ",
        {
            "MYSCOOPE_OAUTH_ISSUER_URL": "https://auth.example.com/",
        },
        clear=True,
    )
    def test_oauth_issuer_url_reads_env_and_strips_trailing_slash(self):
        self.assertEqual(
            get_oauth_issuer_url(),
            "https://auth.example.com",
        )

    @patch.dict(
        "os.environ",
        {
            "OPENAI_APPS_CHALLENGE_TOKEN": "challenge-token",
        },
        clear=True,
    )
    def test_openai_apps_challenge_returns_configured_token(self):
        response = openai_apps_challenge(None)

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response.body.decode("utf-8"),
            "challenge-token",
        )

    @patch.dict(
        "os.environ",
        {},
        clear=True,
    )
    def test_openai_apps_challenge_returns_404_when_not_configured(self):
        response = openai_apps_challenge(None)

        self.assertEqual(
            response.status_code,
            404,
        )

    @patch.dict(
        "os.environ",
        {
            "MYSCOOPE_MCP_RESOURCE_URL": "https://myscoope-mcp.onrender.com",
            "MYSCOOPE_OAUTH_ISSUER_URL": "https://www.myscoope.com",
        },
        clear=True,
    )
    def test_oauth_protected_resource_metadata(self):
        response = oauth_protected_resource_metadata(None)

        self.assertEqual(
            response.status_code,
            200,
        )

        data = json.loads(
            response.body.decode("utf-8"),
        )

        self.assertEqual(
            data["resource"],
            "https://myscoope-mcp.onrender.com",
        )
        self.assertEqual(
            data["authorization_servers"],
            [
                "https://www.myscoope.com",
            ],
        )
        self.assertEqual(
            data["scopes_supported"],
            [
                "myscoope:read",
                "myscoope:proposals:create",
            ],
        )
        self.assertEqual(
            data["resource_documentation"],
            "https://www.myscoope.com/support/",
        )

    @patch.dict(
        "os.environ",
        {
            "MYSCOOPE_MCP_ALLOWED_TOOLS": "read_dailyplan,read_meal",
        },
        clear=True,
    )
    def test_read_only_tool_surface_advertises_only_read_scope(self):
        self.assertEqual(
            get_protected_resource_scopes(),
            ["myscoope:read"],
        )

    @patch.dict(
        "os.environ",
        {
            "MYSCOOPE_MCP_ALLOWED_TOOLS": (
                "read_dailyplan,create_nutrition_engine_dailyplan_proposal"
            ),
        },
        clear=True,
    )
    def test_proposal_tool_surface_advertises_proposal_scope(self):
        self.assertEqual(
            get_protected_resource_scopes(),
            ["myscoope:read", "myscoope:proposals:create"],
        )


if __name__ == "__main__":
    unittest.main()
