import os
from dataclasses import replace
from typing import Any

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from myscoope_mcp.auth import (
    MCP_SCOPE_PROPOSALS_CREATE,
    MCP_SCOPE_READ,
    user_tokens_only_enabled,
)
from myscoope_mcp.client import MyscoopeAPIClient
from myscoope_mcp.config import load_config_from_env
from myscoope_mcp.contracts import MCPToolCallResult
from myscoope_mcp.dispatcher import dispatch_tool_call
from myscoope_mcp.tools import (
    FORBIDDEN_TOOL_NAMES,
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
    TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_LIST_FOOD_CATALOG,
    TOOL_LIST_USER_PROPOSALS,
    TOOL_READ_DAILYPLAN,
    TOOL_READ_PROPOSAL,
)

SERVER_NAME = "my-scoope-mcp"


class MyScoopeFastMCP(FastMCP):
    async def list_tools(self):
        tools = await super().list_tools()
        for tool in tools:
            scopes = [MCP_SCOPE_READ]
            if tool.name in {
                TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
                TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
                TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
                TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
                TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
            }:
                scopes.append(MCP_SCOPE_PROPOSALS_CREATE)
            tool.securitySchemes = [{"type": "oauth2", "scopes": scopes}]
        return tools

READ_ONLY_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    openWorldHint=False,
)

PROPOSAL_CREATE_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    openWorldHint=False,
)


def get_protocol_tool_annotations() -> dict[str, ToolAnnotations]:
    return {
        TOOL_LIST_USER_PROPOSALS: READ_ONLY_TOOL_ANNOTATIONS,
        TOOL_LIST_FOOD_CATALOG: READ_ONLY_TOOL_ANNOTATIONS,
        TOOL_READ_DAILYPLAN: READ_ONLY_TOOL_ANNOTATIONS,
        TOOL_READ_PROPOSAL: READ_ONLY_TOOL_ANNOTATIONS,
        TOOL_COMPARE_DAILYPLAN_TO_TARGETS: READ_ONLY_TOOL_ANNOTATIONS,
        TOOL_CREATE_VALIDATED_MEAL_PROPOSAL: PROPOSAL_CREATE_TOOL_ANNOTATIONS,
        TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL: PROPOSAL_CREATE_TOOL_ANNOTATIONS,
        TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL: PROPOSAL_CREATE_TOOL_ANNOTATIONS,
        TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: PROPOSAL_CREATE_TOOL_ANNOTATIONS,
        TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: PROPOSAL_CREATE_TOOL_ANNOTATIONS,
    }


def _should_forward_mcp_bearer_token(
    token: str | None,
) -> bool:
    if not token:
        return False

    return token.startswith("mcp_user_")


def create_api_client(required_scope: str = MCP_SCOPE_READ) -> MyscoopeAPIClient:
    config = load_config_from_env()
    access_token = get_access_token()
    current_bearer_token = access_token.token if access_token else None

    if user_tokens_only_enabled() and not _should_forward_mcp_bearer_token(current_bearer_token):
        raise RuntimeError("A user-scoped MCP token is required.")

    if _should_forward_mcp_bearer_token(current_bearer_token) and (
        access_token is None or required_scope not in access_token.scopes
    ):
        raise PermissionError("MCP token lacks the required tool scope.")

    if _should_forward_mcp_bearer_token(current_bearer_token):
        config = replace(
            config,
            auth_token=current_bearer_token,
        )

    return MyscoopeAPIClient(config)


def serialize_tool_result(
    result: MCPToolCallResult,
) -> dict[str, Any]:
    """
    Preserve the My Scoope ok/data/error contract for MCP responses.
    """
    return result.as_dict()


def summarize_created_proposal_result(result: MCPToolCallResult) -> dict[str, Any]:
    """Keep nutrition/profile snapshots out of the automatic MCP response."""
    if not result.ok:
        error = result.error or {}
        return {
            "ok": False,
            "data": {},
            "error": {
                "code": error.get("code", "proposal_creation_failed"),
                "message": "Proposal creation failed.",
                "details": {},
            },
        }

    proposal = result.data.get("proposal")
    if not isinstance(proposal, dict) or not isinstance(proposal.get("id"), int):
        return serialize_tool_result(MCPToolCallResult(
            ok=False,
            data={},
            error={
                "code": "invalid_proposal_result",
                "message": "The proposal was created but its reference was unavailable.",
                "details": {},
            },
        ))

    return {
        "ok": True,
        "data": {
            "proposal_id": proposal["id"],
            "status": proposal.get("status"),
            "requires_human_review": True,
            "applies_changes": False,
            "detail_tool": TOOL_READ_PROPOSAL,
        },
        "error": None,
    }


def create_mcp_server(
    host: str | None = None,
    port: int | None = None,
    token_verifier: TokenVerifier | None = None,
    auth_settings: AuthSettings | None = None,
) -> FastMCP:
    """
    Create the real MCP protocol server.

    Boundary:
    - This module may import FastMCP.
    - This module may import the MCP dispatcher.
    - This module may create MyscoopeAPIClient.
    - This module must not import Django models, queries or commands.
    - Food tools may expose operational My Scoope Food IDs only.
    """
    assert_protocol_tool_surface_is_safe()

    server_kwargs: dict[str, Any] = {
        "stateless_http": True,
        "json_response": True,
    }

    if host is not None:
        server_kwargs["host"] = host

    if port is not None:
        server_kwargs["port"] = port

    if token_verifier is not None:
        server_kwargs["token_verifier"] = token_verifier

    if auth_settings is not None:
        server_kwargs["auth"] = auth_settings

    server = MyScoopeFastMCP(
        SERVER_NAME,
        **server_kwargs,
    )

    register_mcp_tools(server)

    for tool_name in get_protocol_allowed_tool_names() - get_configured_allowed_tool_names():
        server.remove_tool(tool_name)

    return server


def register_mcp_tools(server: FastMCP) -> None:
    """
    Register real MCP tools.

    Every tool routes through dispatch_tool_call.
    This keeps the protocol wrapper thin and prevents bypassing the
    API Adapter / Internal AI Tools boundaries.
    """
    annotations = get_protocol_tool_annotations()

    @server.tool(
        annotations=annotations[TOOL_LIST_USER_PROPOSALS],
    )
    def list_user_proposals() -> dict[str, Any]:
        """
        List proposals visible to the authenticated My Scoope API context.
        """
        client = create_api_client()

        result = dispatch_tool_call(
            client=client,
            tool_name=TOOL_LIST_USER_PROPOSALS,
            arguments={},
        )

        return serialize_tool_result(result)

    @server.tool(
        annotations=annotations[TOOL_LIST_FOOD_CATALOG],
    )
    def list_food_catalog(
        search: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        List operational foods available for AI/MCP nutrition planning.

        Returned IDs are operational My Scoope Food IDs only.
        This tool is read-only.
        It does not create foods, meals or dailyplans.
        """
        client = create_api_client()

        arguments = {
            "limit": limit,
        }

        if search is not None:
            arguments["search"] = search

        result = dispatch_tool_call(
            client=client,
            tool_name=TOOL_LIST_FOOD_CATALOG,
            arguments=arguments,
        )

        return serialize_tool_result(result)

    @server.tool(
        annotations=annotations[TOOL_READ_DAILYPLAN],
    )
    def read_dailyplan(dailyplan_id: int) -> dict[str, Any]:
        """
        Read a DailyPlan available to the authenticated My Scoope API context.
        """
        client = create_api_client()

        result = dispatch_tool_call(
            client=client,
            tool_name=TOOL_READ_DAILYPLAN,
            arguments={
                "dailyplan_id": dailyplan_id,
            },
        )

        return serialize_tool_result(result)

    @server.tool(
        annotations=annotations[TOOL_READ_PROPOSAL],
    )
    def read_proposal(proposal_id: int) -> dict[str, Any]:
        """
        Read a NutritionProposal available to the authenticated My Scoope API context.
        """
        client = create_api_client()

        result = dispatch_tool_call(
            client=client,
            tool_name=TOOL_READ_PROPOSAL,
            arguments={
                "proposal_id": proposal_id,
            },
        )

        return serialize_tool_result(result)

    @server.tool(
        annotations=annotations[TOOL_COMPARE_DAILYPLAN_TO_TARGETS],
    )
    def compare_dailyplan_to_targets(
        dailyplan_id: int,
        targets: dict[str, Any],
        tolerances: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Compare a DailyPlan against nutritional targets.

        This tool only validates and compares.
        It does not modify the DailyPlan.
        """
        client = create_api_client()

        arguments = {
            "dailyplan_id": dailyplan_id,
            "targets": targets,
        }

        if tolerances is not None:
            arguments["tolerances"] = tolerances

        result = dispatch_tool_call(
            client=client,
            tool_name=TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
            arguments=arguments,
        )

        return serialize_tool_result(result)

    @server.tool(
        annotations=annotations[TOOL_CREATE_VALIDATED_MEAL_PROPOSAL],
    )
    def create_validated_meal_proposal(
        dailyplan_id: int,
        title: str,
        proposed_payload: dict[str, Any],
        targets: dict[str, Any] | None = None,
        summary: str = "",
    ) -> dict[str, Any]:
        """
        Create a reviewable meal proposal from a rich create_meal payload.

        This tool does not create a final Meal.
        It only creates a NutritionProposal pending human review.
        """
        client = create_api_client(required_scope=MCP_SCOPE_PROPOSALS_CREATE)

        arguments = {
            "dailyplan_id": dailyplan_id,
            "title": title,
            "summary": summary,
            "proposed_payload": proposed_payload,
        }

        if targets is not None:
            arguments["targets"] = targets

        result = dispatch_tool_call(
            client=client,
            tool_name=TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
            arguments=arguments,
        )

        return summarize_created_proposal_result(result)

    @server.tool(
        annotations=annotations[TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL],
    )
    def create_validated_dailyplan_proposal(
        dailyplan_id: int,
        title: str,
        targets: dict[str, Any],
        proposed_payload: dict[str, Any] | None = None,
        tolerances: dict[str, Any] | None = None,
        summary: str = "",
    ) -> dict[str, Any]:
        """
        Create a validated NutritionProposal for human review.

        This tool creates a proposal.
        It does not approve it.
        It does not apply final changes.
        """
        client = create_api_client(required_scope=MCP_SCOPE_PROPOSALS_CREATE)

        arguments = {
            "dailyplan_id": dailyplan_id,
            "title": title,
            "targets": targets,
        }

        if summary:
            arguments["summary"] = summary

        if proposed_payload is not None:
            arguments["proposed_payload"] = proposed_payload

        if tolerances is not None:
            arguments["tolerances"] = tolerances

        result = dispatch_tool_call(
            client=client,
            tool_name=TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
            arguments=arguments,
        )

        return summarize_created_proposal_result(result)

    @server.tool(
        annotations=annotations[TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL],
    )
    def create_validated_dailyplan_build_proposal(
        dailyplan_id: int,
        title: str,
        proposed_payload: dict[str, Any],
        targets: dict[str, Any] | None = None,
        summary: str = "",
    ) -> dict[str, Any]:
        """
        Create a reviewable DailyPlan build proposal from a rich create_dailyplan payload.

        This tool does not create a final DailyPlan.
        It only creates a NutritionProposal pending human review.
        """
        client = create_api_client(required_scope=MCP_SCOPE_PROPOSALS_CREATE)

        arguments: dict[str, Any] = {
            "dailyplan_id": dailyplan_id,
            "title": title,
            "summary": summary,
            "proposed_payload": proposed_payload,
        }

        if targets is not None:
            arguments["targets"] = targets

        result = dispatch_tool_call(
            client=client,
            tool_name=TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
            arguments=arguments,
        )

        return summarize_created_proposal_result(result)


    @server.tool(
        annotations=annotations[TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL],
    )
    def create_nutrition_engine_dailyplan_proposal(
        nutrition_brief: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create a reviewable DailyPlan proposal using the internal nutrition engine.

        This tool creates NutritionProposal artifacts only.
        It does not apply a final DailyPlan.
        """
        client = create_api_client(required_scope=MCP_SCOPE_PROPOSALS_CREATE)

        result = dispatch_tool_call(
            client=client,
            tool_name=TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
            arguments={
                "nutrition_brief": nutrition_brief,
            },
        )

        return summarize_created_proposal_result(result)

    @server.tool(
        annotations=annotations[TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL],
    )
    def iterate_nutrition_engine_dailyplan_proposal(
        previous_proposal_id: int,
        nutrition_brief: dict[str, Any],
        user_message: str,
    ) -> dict[str, Any]:
        """
        Create a new reviewable DailyPlan proposal revision from chat feedback.

        This tool keeps the previous proposal immutable and stores iteration trace.
        """
        client = create_api_client(required_scope=MCP_SCOPE_PROPOSALS_CREATE)

        result = dispatch_tool_call(
            client=client,
            tool_name=TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
            arguments={
                "previous_proposal_id": previous_proposal_id,
                "nutrition_brief": nutrition_brief,
                "user_message": user_message,
            },
        )

        return summarize_created_proposal_result(result)


def get_protocol_allowed_tool_names() -> set[str]:
    """
    Tool names allowed to be exposed by the real MCP protocol wrapper.
    """
    return {
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
    }


def get_configured_allowed_tool_names() -> set[str]:
    """Keep the default surface stable and allow a smaller validation rollout."""
    known = get_protocol_allowed_tool_names()
    raw = os.getenv("MYSCOOPE_MCP_ALLOWED_TOOLS", "").strip()
    if not raw:
        return known
    configured = {name.strip() for name in raw.split(",") if name.strip()}
    if not configured or not configured.issubset(known):
        raise RuntimeError("MYSCOOPE_MCP_ALLOWED_TOOLS contains an unsupported tool.")
    return configured


def get_protocol_forbidden_tool_names() -> set[str]:
    """
    Explicitly forbidden tool names at the protocol wrapper boundary.
    """
    return set(FORBIDDEN_TOOL_NAMES)


def assert_protocol_tool_surface_is_safe() -> None:
    """
    Guardrail to ensure the protocol wrapper never exposes forbidden tools.
    """
    allowed = get_protocol_allowed_tool_names()
    forbidden = get_protocol_forbidden_tool_names()

    overlap = allowed.intersection(forbidden)

    if overlap:
        raise RuntimeError(
            f"Forbidden MCP tools cannot be exposed: {sorted(overlap)}"
        )


def protocol_dispatch_placeholder():
    """
    Placeholder reference proving that the protocol wrapper depends on
    dispatch_tool_call as the routing boundary.
    """
    return dispatch_tool_call
