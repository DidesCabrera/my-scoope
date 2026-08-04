"""MCP projection of the canonical AI Assistant capability catalog.

The source of truth lives in ``ai_assistant.application.tools.registry``.
This module keeps the public MCP constants and ``MCPToolSpec`` adapter stable
without maintaining a second set of descriptions or schemas.
"""

from ai_assistant.application.tools.registry import (
    FORBIDDEN_TOOL_NAMES as CANONICAL_FORBIDDEN_TOOL_NAMES,
)
from ai_assistant.application.tools.registry import (
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
    TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_LIST_USER_PROPOSALS,
    TOOL_READ_DAILYPLAN,
    TOOL_READ_PROPOSAL,
    normalize_tool_name,
)
from ai_assistant.application.tools.registry import (
    get_mcp_tool_spec as get_canonical_mcp_tool_spec,
)
from ai_assistant.application.tools.registry import (
    list_mcp_tool_specs as list_canonical_mcp_tool_specs,
)
from myscoope_mcp.contracts import MCPToolSpec

# Historical MCP compatibility name. The canonical capability is
# ``list_operational_foods`` and still exposes only ``notas.Food``.
TOOL_LIST_FOOD_CATALOG = "list_food_catalog"


FORBIDDEN_TOOL_NAMES = {
    name
    for name in CANONICAL_FORBIDDEN_TOOL_NAMES
    if name != TOOL_LIST_FOOD_CATALOG
}


def _as_mcp_spec(spec) -> MCPToolSpec:
    return MCPToolSpec(
        name=spec.mcp_name,
        description=spec.description,
        api_path=spec.mcp_api_path,
        input_schema=dict(spec.mcp_input_schema or spec.input_schema),
    )


def list_allowed_tool_specs() -> list[MCPToolSpec]:
    return [
        _as_mcp_spec(spec)
        for spec in list_canonical_mcp_tool_specs()
    ]


def get_tool_spec(tool_name: str) -> MCPToolSpec:
    normalized = normalize_tool_name(tool_name)
    try:
        spec = get_canonical_mcp_tool_spec(normalized)
    except ValueError as exc:
        raise ValueError(f"unsupported_mcp_tool:{normalized}") from exc
    return _as_mcp_spec(spec)


def is_forbidden_tool_name(tool_name: str) -> bool:
    return normalize_tool_name(tool_name) in FORBIDDEN_TOOL_NAMES
