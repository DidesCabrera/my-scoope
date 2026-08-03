from __future__ import annotations

from typing import Any, Iterable

from ai_assistant.application.tools.contracts import (
    AssistantToolCategory,
    AssistantToolRegistryError,
    AssistantToolSpec,
)
from ai_assistant.domain.contracts import (
    AssistantToolRequest,
    AssistantToolResult,
    AssistantToolStatus,
)

from ai_assistant.application.tools.tool_names import *  # noqa: F403
from ai_assistant.application.tools.tool_spec_modules.actions import ACTIONS_TOOL_SPECS
from ai_assistant.application.tools.tool_spec_modules.intake import INTAKE_TOOL_SPECS
from ai_assistant.application.tools.tool_spec_modules.proposals import PROPOSALS_TOOL_SPECS
from ai_assistant.application.tools.tool_spec_modules.read import READ_TOOL_SPECS

FORBIDDEN_TOOL_NAMES = {
    "apply_approved_proposal",
    "apply_proposal",
    "apply_validated_proposal",
    "create_dailyplan",
    "create_food",
    "create_meal",
    "delete_dailyplan",
    "delete_food",
    "delete_meal",
    "direct_model_write",
    "list_catalog_foods",
    "list_food_catalog",
    "raw_command_execution",
    "raw_model_mutation",
    "raw_sql",
    "read_catalog_food",
    "search_catalog_foods",
    "search_food_catalog",
    "update_dailyplan",
    "update_food",
    "update_meal",
}

FORBIDDEN_ARGUMENT_KEYS = {
    "catalog_food_id",
    "catalogfoodid",
}

ALLOWED_TOOL_SPECS = {
    **READ_TOOL_SPECS,
    **INTAKE_TOOL_SPECS,
    **PROPOSALS_TOOL_SPECS,
    **ACTIONS_TOOL_SPECS,
}


def normalize_tool_name(tool_name: str) -> str:
    return " ".join(str(tool_name or "").split()).replace("-", "_").replace(" ", "_").lower()


def is_forbidden_tool_name(tool_name: str) -> bool:
    normalized = normalize_tool_name(tool_name)
    return normalized in FORBIDDEN_TOOL_NAMES or "food_catalog" in normalized or "catalog_food" in normalized


def is_allowed_tool_name(tool_name: str) -> bool:
    return normalize_tool_name(tool_name) in ALLOWED_TOOL_SPECS


def list_allowed_tool_specs(
    *,
    categories: Iterable[AssistantToolCategory | str] | None = None,
) -> list[AssistantToolSpec]:
    specs = list(ALLOWED_TOOL_SPECS.values())
    if categories is None:
        return specs

    allowed_categories = {
        category if isinstance(category, AssistantToolCategory) else AssistantToolCategory(str(category))
        for category in categories
    }
    return [spec for spec in specs if spec.category in allowed_categories]


def _strict_proposal_preferences_provider_schema() -> dict[str, Any]:
    """Return the compact strict schema used by provider-native calling.

    All update fields are present and nullable so OpenAI strict function
    calling cannot silently omit a user-stated proposal preference such as
    ``algo simple``. My Scoope removes null values before local validation, so
    fields the user did not state remain absent from the effective update.
    """

    nullable_string = {"type": ["string", "null"]}
    nullable_integer = {"type": ["integer", "null"]}
    update_properties: dict[str, Any] = {
        "goal": {
            "type": ["string", "null"],
            "enum": ["fat_loss", "muscle_gain", "maintenance", "performance", "healthy_eating", None],
        },
        "requested_entity": {
            "type": ["string", "null"],
            "enum": ["daily_plan", "program", None],
        },
        "meals_per_day": {**nullable_integer, "minimum": 1, "maximum": 8},
        "complexity_level": {
            "type": ["string", "null"],
            "enum": ["low", "medium", "high", None],
            "description": "Use low for algo simple/sencillo, medium for intermedio, high for elaborado/complejo.",
        },
        "energy_adjustment": dict(nullable_string),
        "calorie_target": dict(nullable_integer),
        "protein_target": dict(nullable_integer),
        "carb_target": dict(nullable_integer),
        "fat_target": dict(nullable_integer),
        "notes": {"type": ["array", "null"], "items": {"type": "string"}},
    }
    return {
        "type": "object",
        "properties": {
            "updates": {
                "type": "object",
                "properties": update_properties,
                "required": list(update_properties),
                "additionalProperties": False,
            },
        },
        "required": ["updates"],
        "additionalProperties": False,
    }


def list_provider_tool_specs() -> list[dict[str, Any]]:
    provider_specs: list[dict[str, Any]] = []
    for spec in list_allowed_tool_specs():
        if not spec.provider_exposed:
            continue
        provider_spec = spec.as_provider_tool()
        if spec.name == TOOL_UPDATE_PROPOSAL_PREFERENCES:
            provider_spec = {
                **provider_spec,
                "parameters": _strict_proposal_preferences_provider_schema(),
                "strict": True,
            }
        if spec.name == TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS:
            provider_spec = {
                **provider_spec,
                "description": (
                    "Create the requested reviewable DailyPlan proposal from the "
                    "current conversation workspace. My Scoope supplies all known "
                    "drafts and defaults automatically; never fabricate them."
                ),
                "parameters": {
                    "type": "object",
                    "required": [],
                    "properties": {},
                    "additionalProperties": False,
                },
                "strict": True,
            }
        provider_specs.append(provider_spec)
    return provider_specs


def list_mcp_tool_specs() -> list[AssistantToolSpec]:
    """Return the MCP projection of the canonical Assistant capability catalog."""

    return [
        spec
        for spec in list_allowed_tool_specs()
        if spec.mcp_exposed
    ]


def get_mcp_tool_spec(tool_name: str) -> AssistantToolSpec:
    normalized = normalize_tool_name(tool_name)
    for spec in list_mcp_tool_specs():
        if spec.mcp_name == normalized:
            return spec
    raise AssistantToolRegistryError(f"unsupported_mcp_tool:{normalized}")


def get_tool_spec(tool_name: str) -> AssistantToolSpec:
    normalized = normalize_tool_name(tool_name)
    if is_forbidden_tool_name(normalized):
        raise AssistantToolRegistryError(f"forbidden_ai_assistant_tool:{normalized}")
    try:
        return ALLOWED_TOOL_SPECS[normalized]
    except KeyError as exc:
        raise AssistantToolRegistryError(f"unsupported_ai_assistant_tool:{normalized}") from exc


def validate_tool_request(request: AssistantToolRequest) -> AssistantToolResult:
    """Validate a future tool call against the AI Assistant allowlist.

    The returned result is `pending` when the request is allowed. This function
    does not execute tools; it only creates a safe boundary that Patch 46 can use
    before dispatching to My Scoope services.
    """

    normalized_request = AssistantToolRequest(
        tool_name=request.tool_name,
        arguments=request.arguments,
        request_id=request.request_id,
        reason=request.reason,
        metadata=request.metadata,
    )
    tool_name = normalized_request.tool_name

    if is_forbidden_tool_name(tool_name):
        return _blocked_result(
            normalized_request,
            error_code="forbidden_ai_assistant_tool",
            error_message="This tool is explicitly forbidden for the AI Assistant.",
        )

    spec = ALLOWED_TOOL_SPECS.get(tool_name)
    if spec is None:
        return _blocked_result(
            normalized_request,
            error_code="unsupported_ai_assistant_tool",
            error_message="This tool is not part of the AI Assistant allowlist.",
        )

    missing_arguments = _missing_required_arguments(spec, normalized_request.arguments)
    if missing_arguments:
        return _blocked_result(
            normalized_request,
            error_code="invalid_ai_assistant_tool_arguments",
            error_message="Tool request is missing required arguments.",
            details={"missing_arguments": missing_arguments},
        )

    forbidden_argument_key = _find_forbidden_argument_key(normalized_request.arguments)
    if forbidden_argument_key:
        return _blocked_result(
            normalized_request,
            error_code="forbidden_catalog_reference",
            error_message="AI Assistant tools only accept operational notas.Food identifiers.",
            details={"argument_key": forbidden_argument_key},
        )

    return AssistantToolResult(
        tool_name=tool_name,
        status=AssistantToolStatus.PENDING,
        request_id=normalized_request.request_id,
        data={
            "category": spec.category.value,
            "risk_level": spec.risk_level.value,
            "requires_auth": spec.requires_auth,
            "requires_human_review": spec.requires_human_review,
        },
    )


def _missing_required_arguments(spec: AssistantToolSpec, arguments: dict[str, Any]) -> list[str]:
    required = spec.input_schema.get("required") or []
    return [argument for argument in required if argument not in arguments]


def _find_forbidden_argument_key(value: Any) -> str:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            normalized_key = normalize_tool_name(str(key)).replace("_", "")
            if normalize_tool_name(str(key)) in FORBIDDEN_ARGUMENT_KEYS or normalized_key in FORBIDDEN_ARGUMENT_KEYS:
                return str(key)
            nested_match = _find_forbidden_argument_key(nested_value)
            if nested_match:
                return nested_match
    elif isinstance(value, list | tuple):
        for nested_value in value:
            nested_match = _find_forbidden_argument_key(nested_value)
            if nested_match:
                return nested_match
    return ""


def _blocked_result(
    request: AssistantToolRequest,
    *,
    error_code: str,
    error_message: str,
    details: dict[str, Any] | None = None,
) -> AssistantToolResult:
    metadata = dict(request.metadata or {})
    if details:
        metadata["details"] = details
    return AssistantToolResult(
        tool_name=request.tool_name,
        status=AssistantToolStatus.BLOCKED,
        request_id=request.request_id,
        error_code=error_code,
        error_message=error_message,
        metadata=metadata,
    )
