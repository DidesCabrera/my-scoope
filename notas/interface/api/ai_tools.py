from notas.application.ai_tools.proposal_tools import (
    create_nutrition_engine_dailyplan_proposal_tool,
    create_validated_dailyplan_build_proposal_tool,
    create_validated_dailyplan_proposal_tool,
    create_validated_meal_proposal_tool,
    iterate_nutrition_engine_dailyplan_proposal_tool,
)
from notas.application.ai_tools.read_tools import (
    list_food_catalog_tool,
    list_user_proposals_tool,
    read_dailyplan_tool,
    read_food_tool,
    read_meal_tool,
    read_proposal_tool,
)
from notas.application.ai_tools.results import (
    tool_error,
    tool_success,
)
from notas.application.ai_tools.validation_tools import (
    compare_dailyplan_to_targets_tool,
)
from notas.application.services.mcp_user_tokens import (
    MCP_SCOPE_PROPOSALS_CREATE,
    MCP_SCOPE_READ,
)
from notas.interface.api.decorators import ai_tool_api_view
from notas.interface.api.responses import ai_tool_json_response


def _missing_required_field_response(field_name: str):
    return ai_tool_json_response(
        tool_error(
            code=f"missing_required_field:{field_name}",
            message=f"Missing required field: {field_name}.",
        ),
        status=400,
    )


@ai_tool_api_view(required_scopes=[MCP_SCOPE_READ])
def ai_tools_health(request):
    return ai_tool_json_response(
        tool_success(
            {
                "status": "ok",
                "adapter": "ai_tools_api",
            }
        )
    )


@ai_tool_api_view(required_scopes=[MCP_SCOPE_READ])
def ai_tools_read_food(request):
    payload = request.ai_tool_payload

    if "food_id" not in payload:
        return _missing_required_field_response("food_id")

    result = read_food_tool(
        request.user,
        payload["food_id"],
    )

    return ai_tool_json_response(result)


@ai_tool_api_view(required_scopes=[MCP_SCOPE_READ])
def ai_tools_read_meal(request):
    payload = request.ai_tool_payload

    if "meal_id" not in payload:
        return _missing_required_field_response("meal_id")

    result = read_meal_tool(
        request.user,
        payload["meal_id"],
    )

    return ai_tool_json_response(result)


@ai_tool_api_view(required_scopes=[MCP_SCOPE_READ])
def ai_tools_read_dailyplan(request):
    payload = request.ai_tool_payload

    if "dailyplan_id" not in payload:
        return _missing_required_field_response("dailyplan_id")

    result = read_dailyplan_tool(
        request.user,
        payload["dailyplan_id"],
    )

    return ai_tool_json_response(result)


@ai_tool_api_view(required_scopes=[MCP_SCOPE_READ])
def ai_tools_read_proposal(request):
    payload = request.ai_tool_payload

    if "proposal_id" not in payload:
        return _missing_required_field_response("proposal_id")

    result = read_proposal_tool(
        request.user,
        payload["proposal_id"],
    )

    return ai_tool_json_response(result)


@ai_tool_api_view(required_scopes=[MCP_SCOPE_READ])
def ai_tools_list_user_proposals(request):
    result = list_user_proposals_tool(
        request.user,
    )

    return ai_tool_json_response(result)


@ai_tool_api_view(required_scopes=[MCP_SCOPE_READ])
def ai_tools_list_food_catalog(request):
    payload = request.ai_tool_payload

    result = list_food_catalog_tool(
        user=request.user,
        search=payload.get("search"),
        limit=payload.get("limit", 50),
    )

    return ai_tool_json_response(result)


@ai_tool_api_view(required_scopes=[MCP_SCOPE_READ])
def ai_tools_compare_dailyplan_to_targets(request):
    payload = request.ai_tool_payload

    if "dailyplan_id" not in payload:
        return _missing_required_field_response("dailyplan_id")

    if "targets" not in payload:
        return _missing_required_field_response("targets")

    result = compare_dailyplan_to_targets_tool(
        user=request.user,
        dailyplan_id=payload["dailyplan_id"],
        targets=payload["targets"],
        tolerances=payload.get("tolerances"),
    )

    return ai_tool_json_response(result)


@ai_tool_api_view(required_scopes=[MCP_SCOPE_PROPOSALS_CREATE])
def ai_tools_create_validated_dailyplan_proposal(request):
    payload = request.ai_tool_payload

    if "dailyplan_id" not in payload:
        return _missing_required_field_response("dailyplan_id")

    if "title" not in payload:
        return _missing_required_field_response("title")

    if "targets" not in payload:
        return _missing_required_field_response("targets")

    result = create_validated_dailyplan_proposal_tool(
        user=request.user,
        dailyplan_id=payload["dailyplan_id"],
        title=payload["title"],
        targets=payload["targets"],
        proposed_payload=payload.get("proposed_payload"),
        tolerances=payload.get("tolerances"),
        summary=payload.get("summary", ""),
    )

    return ai_tool_json_response(result)


@ai_tool_api_view(required_scopes=[MCP_SCOPE_PROPOSALS_CREATE])
def ai_tools_create_validated_meal_proposal(request):
    payload = request.ai_tool_payload

    if "dailyplan_id" not in payload:
        return _missing_required_field_response("dailyplan_id")

    if "title" not in payload:
        return _missing_required_field_response("title")

    if "proposed_payload" not in payload:
        return _missing_required_field_response("proposed_payload")

    result = create_validated_meal_proposal_tool(
        user=request.user,
        dailyplan_id=payload["dailyplan_id"],
        title=payload["title"],
        proposed_payload=payload["proposed_payload"],
        targets=payload.get("targets"),
        summary=payload.get("summary", ""),
    )

    return ai_tool_json_response(result)


@ai_tool_api_view(required_scopes=[MCP_SCOPE_PROPOSALS_CREATE])
def ai_tools_create_validated_dailyplan_build_proposal(request):
    payload = request.ai_tool_payload

    if "dailyplan_id" not in payload:
        return _missing_required_field_response("dailyplan_id")

    if "title" not in payload:
        return _missing_required_field_response("title")

    if "proposed_payload" not in payload:
        return _missing_required_field_response("proposed_payload")

    result = create_validated_dailyplan_build_proposal_tool(
        user=request.user,
        dailyplan_id=payload["dailyplan_id"],
        title=payload["title"],
        proposed_payload=payload["proposed_payload"],
        targets=payload.get("targets"),
        summary=payload.get("summary", ""),
    )

    return ai_tool_json_response(result)


@ai_tool_api_view(required_scopes=[MCP_SCOPE_PROPOSALS_CREATE])
def ai_tools_create_nutrition_engine_dailyplan_proposal(request):
    payload = request.ai_tool_payload

    if "nutrition_brief" not in payload:
        return _missing_required_field_response("nutrition_brief")

    result = create_nutrition_engine_dailyplan_proposal_tool(
        user=request.user,
        nutrition_brief=payload["nutrition_brief"],
    )

    return ai_tool_json_response(result)


@ai_tool_api_view(required_scopes=[MCP_SCOPE_PROPOSALS_CREATE])
def ai_tools_iterate_nutrition_engine_dailyplan_proposal(request):
    payload = request.ai_tool_payload

    if "previous_proposal_id" not in payload:
        return _missing_required_field_response("previous_proposal_id")

    if "nutrition_brief" not in payload:
        return _missing_required_field_response("nutrition_brief")

    if "user_message" not in payload:
        return _missing_required_field_response("user_message")

    result = iterate_nutrition_engine_dailyplan_proposal_tool(
        user=request.user,
        previous_proposal_id=payload["previous_proposal_id"],
        nutrition_brief=payload["nutrition_brief"],
        user_message=payload["user_message"],
    )

    return ai_tool_json_response(result)
