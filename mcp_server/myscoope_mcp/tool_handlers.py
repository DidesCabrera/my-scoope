from typing import Any

from myscoope_mcp.client import MyscoopeAPIClient
from myscoope_mcp.contracts import MCPToolCallResult
from myscoope_mcp.tools import (
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
    TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_LIST_FOOD_CATALOG,
    TOOL_LIST_USER_PROPOSALS,
    TOOL_READ_DAILYPLAN,
    TOOL_READ_PROPOSAL,
    get_tool_spec,
)


def read_dailyplan(
    client: MyscoopeAPIClient,
    dailyplan_id: int,
) -> MCPToolCallResult:
    spec = get_tool_spec(TOOL_READ_DAILYPLAN)

    return client.call_ai_tool_api(
        spec.api_path,
        {
            "dailyplan_id": dailyplan_id,
        },
    )


def read_proposal(
    client: MyscoopeAPIClient,
    proposal_id: int,
) -> MCPToolCallResult:
    spec = get_tool_spec(TOOL_READ_PROPOSAL)

    return client.call_ai_tool_api(
        spec.api_path,
        {
            "proposal_id": proposal_id,
        },
    )


def list_user_proposals(
    client: MyscoopeAPIClient,
) -> MCPToolCallResult:
    spec = get_tool_spec(TOOL_LIST_USER_PROPOSALS)

    return client.call_ai_tool_api(
        spec.api_path,
        {},
    )


def list_food_catalog(
    client: MyscoopeAPIClient,
    search: str | None = None,
    limit: int = 50,
) -> MCPToolCallResult:
    spec = get_tool_spec(TOOL_LIST_FOOD_CATALOG)

    payload: dict[str, Any] = {
        "limit": limit,
    }

    if search is not None:
        payload["search"] = search

    return client.call_ai_tool_api(
        spec.api_path,
        payload,
    )


def compare_dailyplan_to_targets(
    client: MyscoopeAPIClient,
    dailyplan_id: int,
    targets: dict[str, Any],
    tolerances: dict[str, Any] | None = None,
) -> MCPToolCallResult:
    spec = get_tool_spec(TOOL_COMPARE_DAILYPLAN_TO_TARGETS)

    payload: dict[str, Any] = {
        "dailyplan_id": dailyplan_id,
        "targets": targets,
    }

    if tolerances is not None:
        payload["tolerances"] = tolerances

    return client.call_ai_tool_api(
        spec.api_path,
        payload,
    )


def create_validated_dailyplan_proposal(
    client: MyscoopeAPIClient,
    dailyplan_id: int,
    title: str,
    targets: dict[str, Any],
    proposed_payload: dict[str, Any] | None = None,
    tolerances: dict[str, Any] | None = None,
    summary: str = "",
) -> MCPToolCallResult:
    spec = get_tool_spec(TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL)

    payload: dict[str, Any] = {
        "dailyplan_id": dailyplan_id,
        "title": title,
        "targets": targets,
    }

    if summary:
        payload["summary"] = summary

    if proposed_payload is not None:
        payload["proposed_payload"] = proposed_payload

    if tolerances is not None:
        payload["tolerances"] = tolerances

    return client.call_ai_tool_api(
        spec.api_path,
        payload,
    )


def create_validated_dailyplan_build_proposal(
    client: MyscoopeAPIClient,
    dailyplan_id: int,
    title: str,
    proposed_payload: dict[str, Any],
    targets: dict[str, Any] | None = None,
    summary: str = "",
) -> MCPToolCallResult:
    spec = get_tool_spec(TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL)

    payload: dict[str, Any] = {
        "dailyplan_id": dailyplan_id,
        "title": title,
        "summary": summary,
        "proposed_payload": proposed_payload,
    }

    if targets is not None:
        payload["targets"] = targets

    return client.call_ai_tool_api(
        spec.api_path,
        payload,
    )


def create_validated_meal_proposal(
    client: MyscoopeAPIClient,
    dailyplan_id: int,
    title: str,
    proposed_payload: dict[str, Any],
    targets: dict[str, Any] | None = None,
    summary: str = "",
) -> MCPToolCallResult:
    spec = get_tool_spec(TOOL_CREATE_VALIDATED_MEAL_PROPOSAL)

    payload: dict[str, Any] = {
        "dailyplan_id": dailyplan_id,
        "title": title,
        "summary": summary,
        "proposed_payload": proposed_payload,
    }

    if targets is not None:
        payload["targets"] = targets

    return client.call_ai_tool_api(
        spec.api_path,
        payload,
    )



def create_nutrition_engine_dailyplan_proposal(
    client: MyscoopeAPIClient,
    nutrition_brief: dict[str, Any],
) -> MCPToolCallResult:
    spec = get_tool_spec(TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL)

    return client.call_ai_tool_api(
        spec.api_path,
        {
            "nutrition_brief": nutrition_brief,
        },
    )


def iterate_nutrition_engine_dailyplan_proposal(
    client: MyscoopeAPIClient,
    previous_proposal_id: int,
    nutrition_brief: dict[str, Any],
    user_message: str,
) -> MCPToolCallResult:
    spec = get_tool_spec(TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL)

    return client.call_ai_tool_api(
        spec.api_path,
        {
            "previous_proposal_id": previous_proposal_id,
            "nutrition_brief": nutrition_brief,
            "user_message": user_message,
        },
    )


READ_TOOL_HANDLERS = {
    TOOL_READ_DAILYPLAN: read_dailyplan,
    TOOL_READ_PROPOSAL: read_proposal,
    TOOL_LIST_USER_PROPOSALS: list_user_proposals,
    TOOL_LIST_FOOD_CATALOG: list_food_catalog,
}


VALIDATION_TOOL_HANDLERS = {
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS: compare_dailyplan_to_targets,
}


PROPOSAL_TOOL_HANDLERS = {
    TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL: create_validated_dailyplan_proposal,
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL: create_validated_meal_proposal,
    TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL: (
        create_validated_dailyplan_build_proposal
    ),
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: (
        create_nutrition_engine_dailyplan_proposal
    ),
    TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: (
        iterate_nutrition_engine_dailyplan_proposal
    ),
}


def _missing_required_argument(argument_name: str) -> MCPToolCallResult:
    return MCPToolCallResult(
        ok=False,
        data={},
        error={
            "code": f"missing_required_argument:{argument_name}",
            "message": f"Missing required argument: {argument_name}.",
            "details": {},
        },
    )


def call_read_tool(
    client: MyscoopeAPIClient,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> MCPToolCallResult:
    arguments = arguments or {}

    if tool_name == TOOL_READ_DAILYPLAN:
        if "dailyplan_id" not in arguments:
            return _missing_required_argument("dailyplan_id")

        return read_dailyplan(
            client=client,
            dailyplan_id=arguments["dailyplan_id"],
        )

    if tool_name == TOOL_READ_PROPOSAL:
        if "proposal_id" not in arguments:
            return _missing_required_argument("proposal_id")

        return read_proposal(
            client=client,
            proposal_id=arguments["proposal_id"],
        )

    if tool_name == TOOL_LIST_USER_PROPOSALS:
        return list_user_proposals(
            client=client,
        )

    if tool_name == TOOL_LIST_FOOD_CATALOG:
        return list_food_catalog(
            client=client,
            search=arguments.get("search"),
            limit=arguments.get("limit", 50),
        )

    return MCPToolCallResult(
        ok=False,
        data={},
        error={
            "code": f"unsupported_read_tool:{tool_name}",
            "message": "Unsupported MCP read tool.",
            "details": {},
        },
    )


def call_validation_tool(
    client: MyscoopeAPIClient,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> MCPToolCallResult:
    arguments = arguments or {}

    if tool_name == TOOL_COMPARE_DAILYPLAN_TO_TARGETS:
        if "dailyplan_id" not in arguments:
            return _missing_required_argument("dailyplan_id")

        if "targets" not in arguments:
            return _missing_required_argument("targets")

        return compare_dailyplan_to_targets(
            client=client,
            dailyplan_id=arguments["dailyplan_id"],
            targets=arguments["targets"],
            tolerances=arguments.get("tolerances"),
        )

    return MCPToolCallResult(
        ok=False,
        data={},
        error={
            "code": f"unsupported_validation_tool:{tool_name}",
            "message": "Unsupported MCP validation tool.",
            "details": {},
        },
    )


def call_proposal_tool(
    client: MyscoopeAPIClient,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> MCPToolCallResult:
    arguments = arguments or {}

    if tool_name == TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL:
        if "dailyplan_id" not in arguments:
            return _missing_required_argument("dailyplan_id")

        if "title" not in arguments:
            return _missing_required_argument("title")

        if "targets" not in arguments:
            return _missing_required_argument("targets")

        return create_validated_dailyplan_proposal(
            client=client,
            dailyplan_id=arguments["dailyplan_id"],
            title=arguments["title"],
            targets=arguments["targets"],
            proposed_payload=arguments.get("proposed_payload"),
            tolerances=arguments.get("tolerances"),
            summary=arguments.get("summary", ""),
        )

    if tool_name == TOOL_CREATE_VALIDATED_MEAL_PROPOSAL:
        if "dailyplan_id" not in arguments:
            return _missing_required_argument("dailyplan_id")

        if "title" not in arguments:
            return _missing_required_argument("title")

        if "proposed_payload" not in arguments:
            return _missing_required_argument("proposed_payload")

        return create_validated_meal_proposal(
            client=client,
            dailyplan_id=arguments["dailyplan_id"],
            title=arguments["title"],
            proposed_payload=arguments["proposed_payload"],
            targets=arguments.get("targets"),
            summary=arguments.get("summary", ""),
        )

    if tool_name == TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL:
        if "dailyplan_id" not in arguments:
            return _missing_required_argument("dailyplan_id")

        if "title" not in arguments:
            return _missing_required_argument("title")

        if "proposed_payload" not in arguments:
            return _missing_required_argument("proposed_payload")

        return create_validated_dailyplan_build_proposal(
            client=client,
            dailyplan_id=arguments["dailyplan_id"],
            title=arguments["title"],
            proposed_payload=arguments["proposed_payload"],
            targets=arguments.get("targets"),
            summary=arguments.get("summary", ""),
        )


    if tool_name == TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL:
        if "nutrition_brief" not in arguments:
            return _missing_required_argument("nutrition_brief")

        return create_nutrition_engine_dailyplan_proposal(
            client=client,
            nutrition_brief=arguments["nutrition_brief"],
        )

    if tool_name == TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL:
        if "previous_proposal_id" not in arguments:
            return _missing_required_argument("previous_proposal_id")

        if "nutrition_brief" not in arguments:
            return _missing_required_argument("nutrition_brief")

        if "user_message" not in arguments:
            return _missing_required_argument("user_message")

        return iterate_nutrition_engine_dailyplan_proposal(
            client=client,
            previous_proposal_id=arguments["previous_proposal_id"],
            nutrition_brief=arguments["nutrition_brief"],
            user_message=arguments["user_message"],
        )

    return MCPToolCallResult(
        ok=False,
        data={},
        error={
            "code": f"unsupported_proposal_tool:{tool_name}",
            "message": "Unsupported MCP proposal tool.",
            "details": {},
        },
    )