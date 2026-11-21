import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Annotated, Any, TypedDict
from urllib.parse import urlsplit

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from myscoope_mcp.auth import (
    MCP_SCOPE_PROPOSALS_CREATE,
    MCP_SCOPE_READ,
    user_tokens_only_enabled,
)
from myscoope_mcp.client import MyscoopeAPIClient
from myscoope_mcp.config import load_config_from_env
from myscoope_mcp.contracts import MCPToolCallResult
from myscoope_mcp.dispatcher import dispatch_tool_call
from myscoope_mcp.proposal_card import build_proposal_card_data
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
    TOOL_READ_FOOD,
    TOOL_READ_MEAL,
    TOOL_READ_PROPOSAL,
    TOOL_SEARCH_USER_DAILYPLANS,
    TOOL_SEARCH_USER_MEALS,
)

SERVER_NAME = "my-scoope-mcp"
FOOD_CARD_RESOURCE_URI = "ui://myscoope/food-card-v1.html"
DAILYPLAN_CARD_RESOURCE_URI = "ui://myscoope/dailyplan-card-v2.html"
PROPOSAL_CARD_RESOURCE_URI = "ui://myscoope/proposal-card-v1.html"
PREVIOUS_DAILYPLAN_CARD_RESOURCE_URI = "ui://myscoope/dailyplan-card-v1.html"
ENTITY_CARD_RESOURCE_PATH = Path(__file__).parent / "ui" / "entity_card_v1.html"
DAILYPLAN_CARD_RESOURCE_PATH = Path(__file__).parent / "ui" / "entity_card_v2.html"
PROPOSAL_CARD_RESOURCE_PATH = Path(__file__).parent / "ui" / "proposal_card_v1.html"
MEAL_CARD_RESOURCE_URI = "ui://myscoope/meal-card-v8.html"
MEAL_CARD_RESOURCE_PATH = Path(__file__).parent / "ui" / "meal_card_v8.html"
RECENT_MEAL_CARD_RESOURCE_URI = "ui://myscoope/meal-card-v7.html"
RECENT_MEAL_CARD_RESOURCE_PATH = Path(__file__).parent / "ui" / "meal_card_v7.html"
PREVIOUS_MEAL_CARD_RESOURCE_URI = "ui://myscoope/meal-card-v6.html"
PREVIOUS_MEAL_CARD_RESOURCE_PATH = Path(__file__).parent / "ui" / "meal_card_v6.html"
V5_MEAL_CARD_RESOURCE_URI = "ui://myscoope/meal-card-v5.html"
V5_MEAL_CARD_RESOURCE_PATH = Path(__file__).parent / "ui" / "meal_card_v5.html"
LEGACY_MEAL_CARD_RESOURCE_URI = "ui://myscoope/meal-card-v4.html"
LEGACY_MEAL_CARD_RESOURCE_PATH = Path(__file__).parent / "ui" / "meal_card_v4.html"
OLDER_MEAL_CARD_RESOURCE_URI = "ui://myscoope/meal-card-v3.html"
OLDER_MEAL_CARD_RESOURCE_PATH = Path(__file__).parent / "ui" / "meal_card_v3.html"
OLDEST_MEAL_CARD_RESOURCE_URI = "ui://myscoope/meal-card-v2.html"
OLDEST_MEAL_CARD_RESOURCE_PATH = Path(__file__).parent / "ui" / "meal_card_v2.html"
MEAL_CARD_MIME_TYPE = "text/html;profile=mcp-app"


class MealReadResult(TypedDict):
    ok: bool
    data: dict[str, Any]
    error: dict[str, Any] | None


class MyScoopeFastMCP(FastMCP):
    async def list_tools(self):
        tools = await super().list_tools()
        for tool in tools:
            scopes = [MCP_SCOPE_READ]
            if tool.name in get_proposal_tool_names():
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
        TOOL_READ_FOOD: READ_ONLY_TOOL_ANNOTATIONS,
        TOOL_READ_MEAL: READ_ONLY_TOOL_ANNOTATIONS,
        TOOL_SEARCH_USER_MEALS: READ_ONLY_TOOL_ANNOTATIONS,
        TOOL_SEARCH_USER_DAILYPLANS: READ_ONLY_TOOL_ANNOTATIONS,
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
        missing_fields = (error.get("details") or {}).get("missing_fields")
        if error.get("code") == "nutrition_brief_has_pending_questions" and isinstance(missing_fields, list):
            safe_fields = [
                field for field in missing_fields
                if field in {"goal", "weight_kg", "height_cm", "age_years", "sex", "activity_level"}
            ]
            if safe_fields:
                return {
                    "ok": False,
                    "data": {},
                    "error": {
                        "code": "nutrition_brief_has_pending_questions",
                        "message": "No proposal was created. Ask the user for the missing fields, then retry.",
                        "details": {"missing_fields": safe_fields},
                    },
                }
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


def summarize_generated_dailyplan_proposal_result(result: MCPToolCallResult) -> dict[str, Any]:
    """Show a safe preview while keeping profile and audit snapshots private."""
    summary = summarize_created_proposal_result(result)
    if not summary["ok"]:
        return summary
    card_data = build_proposal_card_data(result.data.get("proposal"))
    if card_data:
        summary["data"].update(card_data)
    return summary


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
    register_mcp_resources(server)

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
    register_meal_tools(server, annotations)
    register_entity_read_tools(server, annotations)

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
        meta={"ui": {"resourceUri": PROPOSAL_CARD_RESOURCE_URI}},
    )
    def create_nutrition_engine_dailyplan_proposal(
        nutrition_brief: Annotated[dict[str, Any], Field(description=(
            "Use canonical flat keys: goal (fat_loss, muscle_gain, maintenance, performance, healthy_eating), "
            "weight_kg, height_cm, age_years, sex (male or female), activity_level "
            "(sedentary, light, moderate, high, very_high), meals_per_day, requested_entity=daily_plan. "
            "If calorie_target is omitted, goal and all five profile fields are required. "
            "Do not put these facts only in raw_prompt or nested profile_draft. "
            "When the tool returns missing_fields, ask only for those facts before retrying."
        ))],
    ) -> dict[str, Any]:
        """
        Create a reviewable DailyPlan proposal using the internal nutrition engine.

        This tool creates NutritionProposal artifacts only. A successful result returns a pending proposal ID.
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

        return summarize_generated_dailyplan_proposal_result(result)

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


def register_entity_read_tools(
    server: FastMCP,
    annotations: dict[str, ToolAnnotations],
) -> None:
    @server.tool(
        annotations=annotations[TOOL_READ_FOOD],
        meta={"ui": {"resourceUri": FOOD_CARD_RESOURCE_URI}},
    )
    def read_food(food_id: Annotated[int, Field(ge=1)]) -> MealReadResult:
        """Read an authorized Food and show the My Scoope nutrition card.

        When the card renders, use it as the primary display. Add only a short
        contextual sentence, not another nutrition table or card unless asked.
        """
        client = create_api_client()
        result = dispatch_tool_call(client=client, tool_name=TOOL_READ_FOOD, arguments={"food_id": food_id})
        return serialize_tool_result(result)

    @server.tool(
        annotations=annotations[TOOL_READ_DAILYPLAN],
        meta={"ui": {"resourceUri": DAILYPLAN_CARD_RESOURCE_URI}},
    )
    def read_dailyplan(dailyplan_id: int) -> MealReadResult:
        """Read an authorized DailyPlan and show its My Scoope card.

        When the card renders, summarize only what helps answer the question;
        avoid rebuilding the same plan card in prose.
        """
        client = create_api_client()
        result = dispatch_tool_call(
            client=client,
            tool_name=TOOL_READ_DAILYPLAN,
            arguments={"dailyplan_id": dailyplan_id},
        )
        return serialize_tool_result(result)

    @server.tool(
        annotations=annotations[TOOL_SEARCH_USER_DAILYPLANS],
    )
    def search_user_dailyplans(
        query: Annotated[str, Field(min_length=1, max_length=80)],
        limit: Annotated[int, Field(ge=1, le=10)] = 10,
    ) -> dict[str, Any]:
        """Find up to ten readable DailyPlans by name. Ask when several match."""
        client = create_api_client()
        result = dispatch_tool_call(
            client=client,
            tool_name=TOOL_SEARCH_USER_DAILYPLANS,
            arguments={"query": query, "limit": limit},
        )
        return serialize_tool_result(result)


def register_meal_tools(
    server: FastMCP,
    annotations: dict[str, ToolAnnotations],
) -> None:
    @server.tool(
        annotations=annotations[TOOL_READ_MEAL],
        meta={"ui": {"resourceUri": MEAL_CARD_RESOURCE_URI}},
    )
    def read_meal(meal_id: Annotated[int, Field(ge=1)]) -> MealReadResult:
        """Read an authorized Meal and show the My Scoope nutrition card.

        When the card renders, use it as the primary display; avoid a duplicate
        nutrition table unless requested.
        """
        client = create_api_client()
        result = dispatch_tool_call(
            client=client,
            tool_name=TOOL_READ_MEAL,
            arguments={"meal_id": meal_id},
        )
        return serialize_tool_result(result)

    @server.tool(
        annotations=annotations[TOOL_SEARCH_USER_MEALS],
    )
    def search_user_meals(
        query: Annotated[str, Field(min_length=1, max_length=80)],
        limit: Annotated[int, Field(ge=1, le=10)] = 10,
    ) -> dict[str, Any]:
        """Find up to ten readable Meals by name. Ask the user when several match."""
        client = create_api_client()
        result = dispatch_tool_call(
            client=client,
            tool_name=TOOL_SEARCH_USER_MEALS,
            arguments={"query": query, "limit": limit},
        )
        return serialize_tool_result(result)


def get_protocol_allowed_tool_names() -> set[str]:
    """
    Tool names allowed to be exposed by the real MCP protocol wrapper.
    """
    return {
        TOOL_READ_DAILYPLAN,
        TOOL_READ_FOOD,
        TOOL_READ_MEAL,
        TOOL_SEARCH_USER_MEALS,
        TOOL_SEARCH_USER_DAILYPLANS,
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


def get_proposal_tool_names() -> set[str]:
    """Tools that require the proposal-creation OAuth scope."""
    return {
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


def _card_web_app_base_url() -> str:
    configured = (
        os.getenv("MYSCOOPE_CARD_WEB_APP_BASE_URL")
        or load_config_from_env().normalized_api_base_url
    )
    parsed = urlsplit(configured.rstrip("/"))
    if (
        parsed.scheme not in {"http", "https"}
        or (parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"})
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") != "/app"
    ):
        raise ValueError("The MCP card web app base URL must be an absolute /app URL.")
    return f"{parsed.scheme}://{parsed.netloc}/app"


def register_mcp_resources(server: FastMCP) -> None:
    card_app_base_url = _card_web_app_base_url()
    parsed_app_url = urlsplit(card_app_base_url)
    redirect_origin = f"{parsed_app_url.scheme}://{parsed_app_url.netloc}"
    @server.resource(
        FOOD_CARD_RESOURCE_URI,
        name="My Scoope food card",
        mime_type=MEAL_CARD_MIME_TYPE,
        meta={"openai/widgetCSP": {"resource_domains": [redirect_origin]}},
    )
    def food_card_resource() -> str:
        return ENTITY_CARD_RESOURCE_PATH.read_text(encoding="utf-8").replace(
            '"__MYSCOOPE_IMAGE_ORIGIN__"', json.dumps(redirect_origin)
        )

    @server.resource(
        DAILYPLAN_CARD_RESOURCE_URI,
        name="My Scoope daily plan card",
        mime_type=MEAL_CARD_MIME_TYPE,
        meta={"openai/widgetCSP": {"redirect_domains": [redirect_origin], "resource_domains": [redirect_origin]}},
    )
    def dailyplan_card_resource() -> str:
        return DAILYPLAN_CARD_RESOURCE_PATH.read_text(encoding="utf-8").replace(
            '"__MYSCOOPE_APP_BASE_URL__"', json.dumps(card_app_base_url)
        ).replace(
            '"__MYSCOOPE_IMAGE_ORIGIN__"', json.dumps(redirect_origin)
        )

    @server.resource(
        PROPOSAL_CARD_RESOURCE_URI,
        name="My Scoope proposal card",
        mime_type=MEAL_CARD_MIME_TYPE,
        meta={"openai/widgetCSP": {"redirect_domains": [redirect_origin], "resource_domains": [redirect_origin]}},
    )
    def proposal_card_resource() -> str:
        return PROPOSAL_CARD_RESOURCE_PATH.read_text(encoding="utf-8").replace(
            '"__MYSCOOPE_APP_BASE_URL__"', json.dumps(card_app_base_url)
        ).replace(
            '"__MYSCOOPE_IMAGE_ORIGIN__"', json.dumps(redirect_origin)
        )

    @server.resource(PREVIOUS_DAILYPLAN_CARD_RESOURCE_URI, name="My Scoope daily plan card v1", mime_type=MEAL_CARD_MIME_TYPE)
    def previous_dailyplan_card_resource() -> str:
        return ENTITY_CARD_RESOURCE_PATH.read_text(encoding="utf-8")

    @server.resource(
        MEAL_CARD_RESOURCE_URI,
        name="My Scoope meal card",
        mime_type=MEAL_CARD_MIME_TYPE,
        meta={"openai/widgetCSP": {"redirect_domains": [redirect_origin], "resource_domains": [redirect_origin]}},
    )
    def meal_card_resource() -> str:
        return MEAL_CARD_RESOURCE_PATH.read_text(encoding="utf-8").replace(
            '"__MYSCOOPE_APP_LINK_ORIGIN__"', json.dumps(redirect_origin)
        )

    @server.resource(
        RECENT_MEAL_CARD_RESOURCE_URI,
        name="My Scoope meal card v7",
        mime_type=MEAL_CARD_MIME_TYPE,
    )
    def recent_meal_card_resource() -> str:
        return RECENT_MEAL_CARD_RESOURCE_PATH.read_text(encoding="utf-8")

    @server.resource(
        PREVIOUS_MEAL_CARD_RESOURCE_URI,
        name="My Scoope meal card v6",
        mime_type=MEAL_CARD_MIME_TYPE,
    )
    def previous_meal_card_resource() -> str:
        return PREVIOUS_MEAL_CARD_RESOURCE_PATH.read_text(encoding="utf-8")

    @server.resource(
        V5_MEAL_CARD_RESOURCE_URI,
        name="My Scoope meal card v5",
        mime_type=MEAL_CARD_MIME_TYPE,
    )
    def v5_meal_card_resource() -> str:
        return V5_MEAL_CARD_RESOURCE_PATH.read_text(encoding="utf-8")

    @server.resource(
        LEGACY_MEAL_CARD_RESOURCE_URI,
        name="My Scoope meal card v4",
        mime_type=MEAL_CARD_MIME_TYPE,
    )
    def legacy_meal_card_resource() -> str:
        return LEGACY_MEAL_CARD_RESOURCE_PATH.read_text(encoding="utf-8")

    @server.resource(
        OLDER_MEAL_CARD_RESOURCE_URI,
        name="My Scoope meal card v3",
        mime_type=MEAL_CARD_MIME_TYPE,
    )
    def older_meal_card_resource() -> str:
        return OLDER_MEAL_CARD_RESOURCE_PATH.read_text(encoding="utf-8")

    @server.resource(
        OLDEST_MEAL_CARD_RESOURCE_URI,
        name="My Scoope meal card v2",
        mime_type=MEAL_CARD_MIME_TYPE,
    )
    def oldest_meal_card_resource() -> str:
        return OLDEST_MEAL_CARD_RESOURCE_PATH.read_text(encoding="utf-8")
