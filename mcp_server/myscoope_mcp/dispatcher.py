from typing import Any

from myscoope_mcp.client import MyscoopeAPIClient
from myscoope_mcp.contracts import MCPToolCallResult
from myscoope_mcp.tool_handlers import (
    call_proposal_tool,
    call_read_tool,
    call_validation_tool,
)
from myscoope_mcp.tools import (
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
    TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_LIST_USER_PROPOSALS,
    TOOL_READ_DAILYPLAN,
    TOOL_READ_PROPOSAL,
    TOOL_LIST_FOOD_CATALOG,
    is_forbidden_tool_name,
)


READ_TOOL_NAMES = {
    TOOL_READ_DAILYPLAN,
    TOOL_READ_PROPOSAL,
    TOOL_LIST_USER_PROPOSALS,
    TOOL_LIST_FOOD_CATALOG,
}


VALIDATION_TOOL_NAMES = {
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
}


PROPOSAL_TOOL_NAMES = {
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
}


def dispatch_tool_call(
    client: MyscoopeAPIClient,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> MCPToolCallResult:
    """
    Single internal dispatcher for MCP tool calls.

    This is not the MCP protocol server yet.
    It is the safe routing boundary used by the future MCP server.
    """
    arguments = arguments or {}

    if is_forbidden_tool_name(tool_name):
        return MCPToolCallResult(
            ok=False,
            data={},
            error={
                "code": f"forbidden_mcp_tool:{tool_name}",
                "message": "This MCP tool is explicitly forbidden.",
                "details": {},
            },
        )

    if tool_name in READ_TOOL_NAMES:
        return call_read_tool(
            client=client,
            tool_name=tool_name,
            arguments=arguments,
        )

    if tool_name in VALIDATION_TOOL_NAMES:
        return call_validation_tool(
            client=client,
            tool_name=tool_name,
            arguments=arguments,
        )

    if tool_name in PROPOSAL_TOOL_NAMES:
        return call_proposal_tool(
            client=client,
            tool_name=tool_name,
            arguments=arguments,
        )

    return MCPToolCallResult(
        ok=False,
        data={},
        error={
            "code": f"unsupported_mcp_tool:{tool_name}",
            "message": "Unsupported MCP tool.",
            "details": {},
        },
    )