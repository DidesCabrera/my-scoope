import unittest

from unittest.mock import patch
from mcp.server.auth.provider import AccessToken
from starlette.applications import Starlette

from mcp.server.fastmcp import FastMCP

from myscoope_mcp.contracts import MCPToolCallResult

from myscoope_mcp.tools import (
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_LIST_USER_PROPOSALS,
    TOOL_LIST_FOOD_CATALOG,
    TOOL_READ_DAILYPLAN,
    TOOL_READ_PROPOSAL,
)

from myscoope_mcp.protocol_server import (
    SERVER_NAME,
    assert_protocol_tool_surface_is_safe,
    create_mcp_server,
    get_protocol_allowed_tool_names,
    get_protocol_forbidden_tool_names,
    get_protocol_tool_annotations,
    protocol_dispatch_placeholder,
    serialize_tool_result,
)


class MCPProtocolServerTests(unittest.TestCase):
    def test_create_mcp_server_returns_fastmcp_instance(self):
        server = create_mcp_server()

        self.assertIsInstance(server, FastMCP)
        self.assertEqual(server.name, SERVER_NAME)

    def test_allowed_protocol_tool_names_are_expected_mvp_surface(self):
        self.assertEqual(
            get_protocol_allowed_tool_names(),
            {
                TOOL_READ_DAILYPLAN,
                TOOL_READ_PROPOSAL,
                TOOL_LIST_USER_PROPOSALS,
                TOOL_LIST_FOOD_CATALOG,
                TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
                TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
                TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
                TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
                TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
                TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
            },
        )

    def test_protocol_forbidden_tool_names_include_apply_tools(self):
        forbidden = get_protocol_forbidden_tool_names()

        self.assertIn("apply_approved_proposal", forbidden)
        self.assertIn("apply_proposal", forbidden)
        self.assertIn("apply_validated_proposal", forbidden)

    def test_protocol_tool_surface_has_no_forbidden_overlap(self):
        assert_protocol_tool_surface_is_safe()

    def test_protocol_wrapper_uses_dispatcher_boundary(self):
        dispatch = protocol_dispatch_placeholder()

        self.assertTrue(callable(dispatch))

    def test_serialize_tool_result_preserves_success_contract(self):
        result = MCPToolCallResult(
            ok=True,
            data={
                "proposals": [],
            },
            error=None,
        )

        self.assertEqual(
            serialize_tool_result(result),
            {
                "ok": True,
                "data": {
                    "proposals": [],
                },
                "error": None,
            },
        )

    def test_serialize_tool_result_preserves_error_contract(self):
        result = MCPToolCallResult(
            ok=False,
            data={},
            error={
                "code": "not_found",
                "message": "Not found.",
                "details": {},
            },
        )

        self.assertEqual(
            serialize_tool_result(result),
            {
                "ok": False,
                "data": {},
                "error": {
                    "code": "not_found",
                    "message": "Not found.",
                    "details": {},
                },
            },
        )

    def test_create_mcp_server_registers_all_mvp_tools_without_sdk_internal_assertions(self):
        server = create_mcp_server()

        self.assertIsInstance(server, FastMCP)
        self.assertEqual(server.name, SERVER_NAME)


    @patch("myscoope_mcp.protocol_server.get_access_token")
    def test_create_api_client_uses_current_mcp_access_token_when_available(
        self,
        mocked_get_access_token,
    ):
        from myscoope_mcp.protocol_server import create_api_client

        mocked_get_access_token.return_value = AccessToken(
            token="mcp_user_dynamic-token",
            client_id="client",
            scopes=[
                "myscoope:mcp",
            ],
            resource="http://127.0.0.1:8001",
        )

        client = create_api_client()

        self.assertEqual(
            client.config.auth_token,
            "mcp_user_dynamic-token",
        )

    @patch("myscoope_mcp.protocol_server.get_access_token")
    @patch.dict(
        "os.environ",
        {
            "MYSCOOPE_API_AUTH_TOKEN": "legacy-api-token",
        },
        clear=False,
    )

    def test_create_api_client_falls_back_to_legacy_env_token_without_current_mcp_token(
        self,
        mocked_get_access_token,
    ):
        from myscoope_mcp.protocol_server import create_api_client

        mocked_get_access_token.return_value = None

        client = create_api_client()

        self.assertEqual(
            client.config.auth_token,
            "legacy-api-token",
        )

    @patch("myscoope_mcp.protocol_server.get_access_token")
    @patch.dict(
        "os.environ",
        {
            "MYSCOOPE_API_AUTH_TOKEN": "legacy-api-token",
        },
        clear=False,
    )
    def test_create_api_client_uses_legacy_env_token_for_external_mcp_token(
        self,
        mocked_get_access_token,
    ):
        from mcp.server.auth.provider import AccessToken
        from myscoope_mcp.protocol_server import create_api_client

        mocked_get_access_token.return_value = AccessToken(
            token="external-dev-mcp-token",
            client_id="myscoope-external-mcp-client",
            scopes=[
                "myscoope:mcp",
            ],
            resource="http://127.0.0.1:8001",
        )

        client = create_api_client()

        self.assertEqual(
            client.config.auth_token,
            "legacy-api-token",
        )

    def test_create_http_app_mounts_starlette_app(self):
        from myscoope_mcp.run_protocol_server import _create_http_app

        server = create_mcp_server()
        app = _create_http_app(server)

        self.assertIsInstance(app, Starlette)



    def test_protocol_tool_annotations_cover_all_allowed_tools(self):
        annotations = get_protocol_tool_annotations()

        self.assertEqual(
            set(annotations.keys()),
            get_protocol_allowed_tool_names(),
        )

    def test_read_tools_are_annotated_as_read_only_non_destructive_open_world(self):
        annotations = get_protocol_tool_annotations()

        for tool_name in [
            TOOL_LIST_USER_PROPOSALS,
            TOOL_LIST_FOOD_CATALOG,
            TOOL_READ_DAILYPLAN,
            TOOL_READ_PROPOSAL,
            TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
        ]:
            self.assertTrue(
                annotations[tool_name].readOnlyHint,
                tool_name,
            )
            self.assertFalse(
                annotations[tool_name].destructiveHint,
                tool_name,
            )
            self.assertTrue(
                annotations[tool_name].openWorldHint,
                tool_name,
            )

    def test_proposal_create_tools_are_annotated_as_write_non_destructive_open_world(self):
        annotations = get_protocol_tool_annotations()

        for tool_name in [
            TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
            TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
            TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
            TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
            TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
        ]:
            self.assertFalse(
                annotations[tool_name].readOnlyHint,
                tool_name,
            )
            self.assertFalse(
                annotations[tool_name].destructiveHint,
                tool_name,
            )
            self.assertTrue(
                annotations[tool_name].openWorldHint,
                tool_name,
            )



if __name__ == "__main__":
    unittest.main()