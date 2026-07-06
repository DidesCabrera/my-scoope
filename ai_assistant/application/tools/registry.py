from __future__ import annotations

from typing import Any, Iterable

from ai_assistant.application.tools.contracts import (
    AssistantToolCategory,
    AssistantToolRegistryError,
    AssistantToolRiskLevel,
    AssistantToolSpec,
)
from ai_assistant.domain.contracts import (
    AssistantToolRequest,
    AssistantToolResult,
    AssistantToolStatus,
)

TOOL_READ_DAILYPLAN = "read_dailyplan"
TOOL_READ_PROPOSAL = "read_proposal"
TOOL_LIST_USER_PROPOSALS = "list_user_proposals"
TOOL_SEARCH_OPERATIONAL_FOODS = "search_operational_foods"
TOOL_LIST_OPERATIONAL_FOODS = "list_operational_foods"
TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES = "preview_nutrition_solver_candidates"
TOOL_COMPARE_DAILYPLAN_TO_TARGETS = "compare_dailyplan_to_targets"
TOOL_CREATE_VALIDATED_MEAL_PROPOSAL = "create_validated_meal_proposal"
TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL = "create_nutrition_solver_meal_proposal"
TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL = "create_validated_dailyplan_build_proposal"
TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL = "create_nutrition_engine_dailyplan_proposal"
TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL = "iterate_nutrition_engine_dailyplan_proposal"

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
    TOOL_READ_DAILYPLAN: AssistantToolSpec(
        name=TOOL_READ_DAILYPLAN,
        description="Read one operational DailyPlan visible to the authenticated user.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question"),
        input_schema={
            "type": "object",
            "required": ["dailyplan_id"],
            "properties": {
                "dailyplan_id": {
                    "type": "integer",
                    "description": "Operational DailyPlan ID to read.",
                },
            },
        },
    ),
    TOOL_READ_PROPOSAL: AssistantToolSpec(
        name=TOOL_READ_PROPOSAL,
        description="Read one NutritionProposal visible to the authenticated user.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["proposal_id"],
            "properties": {
                "proposal_id": {
                    "type": "integer",
                    "description": "NutritionProposal ID to read.",
                },
            },
        },
    ),
    TOOL_LIST_USER_PROPOSALS: AssistantToolSpec(
        name=TOOL_LIST_USER_PROPOSALS,
        description="List reviewable proposals visible to the authenticated user.",
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=("read_context", "answer_question", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": [],
            "properties": {},
        },
    ),
    TOOL_SEARCH_OPERATIONAL_FOODS: AssistantToolSpec(
        name=TOOL_SEARCH_OPERATIONAL_FOODS,
        description=(
            "Search operational My Scoope foods available for planning. "
            "Returned IDs are notas.Food IDs, never master catalog IDs."
        ),
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.LOW,
        requires_human_review=False,
        allowed_intents=(
            "answer_question",
            "capture_nutrition_brief",
            "create_meal_proposal",
            "create_dailyplan_proposal",
            "iterate_proposal",
        ),
        input_schema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Food name search over operational foods.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Optional maximum number of foods to return.",
                },
            },
        },
    ),
    TOOL_LIST_OPERATIONAL_FOODS: AssistantToolSpec(
        name=TOOL_LIST_OPERATIONAL_FOODS,
        description=(
            "List operational My Scoope foods available for planning. "
            "Returned IDs are notas.Food IDs, never master catalog IDs."
        ),
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.MEDIUM,
        requires_human_review=False,
        allowed_intents=(
            "capture_nutrition_brief",
            "create_meal_proposal",
            "create_dailyplan_proposal",
            "iterate_proposal",
        ),
        input_schema={
            "type": "object",
            "required": [],
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Optional maximum number of foods to return.",
                },
            },
        },
    ),

    TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES: AssistantToolSpec(
        name=TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES,
        description=(
            "Preview solver-ready operational food candidates for the internal nutrition solver. "
            "Returned IDs are notas.Food IDs and the payload never exposes master catalog or external provider fields."
        ),
        category=AssistantToolCategory.READ,
        risk_level=AssistantToolRiskLevel.MEDIUM,
        requires_human_review=False,
        allowed_intents=(
            "answer_question",
            "capture_nutrition_brief",
            "create_dailyplan_proposal",
            "iterate_proposal",
        ),
        input_schema={
            "type": "object",
            "required": [],
            "properties": {
                "search": {
                    "type": "string",
                    "description": "Optional food name search over solver-ready operational foods.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Optional maximum number of solver candidates to preview.",
                },
                "include_extended": {
                    "type": "boolean",
                    "description": "Whether extended operational foods may be included alongside core foods.",
                },
            },
        },
    ),
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS: AssistantToolSpec(
        name=TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
        description="Compare an operational DailyPlan against nutritional targets using My Scoope validation.",
        category=AssistantToolCategory.VALIDATION,
        risk_level=AssistantToolRiskLevel.MEDIUM,
        requires_human_review=False,
        allowed_intents=("answer_question", "create_dailyplan_proposal", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["dailyplan_id", "targets"],
            "properties": {
                "dailyplan_id": {
                    "type": "integer",
                    "description": "Operational DailyPlan ID to validate.",
                },
                "targets": {
                    "type": "object",
                    "description": "Target nutrition metrics.",
                },
                "tolerances": {
                    "type": "object",
                    "description": "Optional tolerance values.",
                },
            },
        },
    ),
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL: AssistantToolSpec(
        name=TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
        description=(
            "Create a reviewable meal proposal through My Scoope services. "
            "This never creates or applies a final Meal directly."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        allowed_intents=("create_meal_proposal", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["dailyplan_id", "title", "proposed_payload"],
            "properties": {
                "dailyplan_id": {"type": "integer"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "targets": {"type": "object"},
                "proposed_payload": {
                    "type": "object",
                    "description": "Meal proposal payload using operational food_id values only.",
                },
            },
        },
    ),

    TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL: AssistantToolSpec(
        name=TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL,
        description=(
            "Create a reviewable Meal proposal by running the internal Nutrition Solver "
            "against solver-ready operational food candidates. This never creates or applies a final Meal directly."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        allowed_intents=("create_meal_proposal", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["dailyplan_id", "title", "target"],
            "properties": {
                "dailyplan_id": {"type": "integer"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "target": {
                    "type": "object",
                    "description": "Meal-level target macros. Supports kcal/total_kcal, protein, carbs and fat.",
                },
                "search": {"type": "string"},
                "limit": {"type": "integer"},
                "include_extended": {"type": "boolean"},
                "meal_slot": {"type": "string"},
            },
        },
    ),
    TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL: AssistantToolSpec(
        name=TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
        description=(
            "Create a reviewable DailyPlan build proposal through My Scoope services. "
            "This never creates or applies a final DailyPlan directly."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        allowed_intents=("create_dailyplan_proposal", "iterate_proposal"),
        input_schema={
            "type": "object",
            "required": ["dailyplan_id", "title", "proposed_payload"],
            "properties": {
                "dailyplan_id": {"type": "integer"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "targets": {"type": "object"},
                "proposed_payload": {
                    "type": "object",
                    "description": "DailyPlan proposal payload using operational food_id values only.",
                },
            },
        },
    ),
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: AssistantToolSpec(
        name=TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
        description=(
            "Create a reviewable DailyPlan proposal by running the internal My Scoope "
            "nutrition engine from a structured NutritionBrief."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        allowed_intents=("capture_nutrition_brief", "create_dailyplan_proposal"),
        input_schema={
            "type": "object",
            "required": ["nutrition_brief"],
            "properties": {
                "nutrition_brief": {
                    "type": "object",
                    "description": "Structured NutritionBrief consumed by the internal nutrition engine.",
                },
            },
        },
    ),
    TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: AssistantToolSpec(
        name=TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
        description=(
            "Create a new reviewable DailyPlan proposal revision from structured user feedback. "
            "This does not mutate or apply the previous proposal."
        ),
        category=AssistantToolCategory.PROPOSAL,
        risk_level=AssistantToolRiskLevel.REVIEW_REQUIRED,
        allowed_intents=("iterate_proposal",),
        input_schema={
            "type": "object",
            "required": ["previous_proposal_id", "nutrition_brief", "user_message"],
            "properties": {
                "previous_proposal_id": {"type": "integer"},
                "nutrition_brief": {"type": "object"},
                "user_message": {"type": "string"},
            },
        },
    ),
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


def list_provider_tool_specs() -> list[dict[str, Any]]:
    return [spec.as_provider_tool() for spec in list_allowed_tool_specs()]


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
