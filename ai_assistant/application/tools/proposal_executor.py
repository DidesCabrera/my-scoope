from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ai_assistant.application.tools.contracts import AssistantToolCategory
from ai_assistant.application.tools.registry import (
    TOOL_CREATE_PROPORTIONAL_DAILYPLAN_CALORIE_PROPOSAL,
    TOOL_PREPARE_PRODUCT_ACTION,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
    TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
    TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    get_tool_spec,
    normalize_tool_name,
    validate_tool_request,
)
from ai_assistant.domain.contracts import (
    AssistantToolRequest,
    AssistantToolResult,
    AssistantToolStatus,
)
from notas.application.ai_tools.results import AIToolResult

ReviewableProposalToolCallable = Callable[..., AIToolResult]


@dataclass(frozen=True)
class ReviewableProposalToolExecutor:
    """Execute only reviewable proposal tools through My Scoope services.

    Patch 55 introduces the first controlled write boundary for the external
    LLM cycle. These tools may create `NutritionProposal` records, but they do
    not create final foods/meals/plans and they never apply proposals. Every
    successful result remains reviewable by a human before any domain mutation
    can be accepted.
    """

    dispatch_table: Mapping[str, ReviewableProposalToolCallable] = field(default_factory=dict)

    def execute(
        self,
        request: AssistantToolRequest,
        *,
        user: Any,
    ) -> AssistantToolResult:
        normalized_request = AssistantToolRequest(
            tool_name=request.tool_name,
            arguments=dict(request.arguments or {}),
            request_id=request.request_id,
            reason=request.reason,
            metadata=request.metadata,
        )
        validation_result = validate_tool_request(normalized_request)
        if validation_result.status != AssistantToolStatus.PENDING:
            return validation_result

        spec = get_tool_spec(normalized_request.tool_name)
        if spec.category != AssistantToolCategory.PROPOSAL:
            return _blocked_result(
                normalized_request,
                error_code="non_reviewable_proposal_tool_blocked",
                error_message="Patch 55 only executes reviewable proposal tools.",
                details={
                    "category": spec.category.value,
                    "risk_level": spec.risk_level.value,
                },
            )

        tool_fn = self._resolve_tool(normalized_request.tool_name)
        if tool_fn is None:
            return _blocked_result(
                normalized_request,
                error_code="reviewable_proposal_tool_not_dispatchable",
                error_message="This proposal tool is not connected to the local executor.",
            )

        try:
            raw_result = tool_fn(user, **dict(normalized_request.arguments or {}))
        except TypeError as exc:
            return _error_result(
                normalized_request,
                error_code="reviewable_proposal_tool_argument_error",
                error_message="Proposal tool arguments could not be dispatched safely.",
                details={"exception": exc.__class__.__name__},
            )

        if raw_result.ok:
            proposal_ids = _extract_proposal_ids(raw_result.data)
            return AssistantToolResult(
                tool_name=normalized_request.tool_name,
                status=AssistantToolStatus.OK,
                request_id=normalized_request.request_id,
                data=dict(raw_result.data or {}),
                metadata={
                    "executor": "reviewable_proposal_tool_executor.v1",
                    "category": spec.category.value,
                    "risk_level": spec.risk_level.value,
                    "requires_human_review": True,
                    "creates_reviewable_proposal": True,
                    "applies_changes": False,
                    "writes_allowed": False,
                    "proposal_ids": list(proposal_ids),
                },
            )

        error = raw_result.error
        return _error_result(
            normalized_request,
            error_code=error.code if error else "reviewable_proposal_tool_error",
            error_message=error.message if error else "Proposal tool execution failed.",
            details=error.details if error else {},
        )

    def _resolve_tool(self, tool_name: str) -> ReviewableProposalToolCallable | None:
        dispatch_table = dict(self.dispatch_table or {})
        if not dispatch_table:
            dispatch_table = build_default_reviewable_proposal_tool_dispatch_table()
        return dispatch_table.get(normalize_tool_name(tool_name))


def build_default_reviewable_proposal_tool_dispatch_table() -> dict[str, ReviewableProposalToolCallable]:
    """Load the local reviewable proposal tool dispatch table lazily."""

    from notas.application.ai_tools.proposal_tools import (
        create_proportional_dailyplan_calorie_proposal_tool,
        create_nutrition_engine_dailyplan_proposal_tool,
        create_nutrition_engine_dailyplan_proposal_from_drafts_tool,
        create_nutrition_solver_meal_proposal_tool,
        create_validated_dailyplan_proposal_tool,
        create_validated_dailyplan_build_proposal_tool,
        create_validated_meal_proposal_tool,
        iterate_nutrition_engine_dailyplan_proposal_tool,
    )
    from ai_assistant.application.tools.prepared_action_tools import (
        prepare_product_action_tool,
    )

    return {
        TOOL_CREATE_PROPORTIONAL_DAILYPLAN_CALORIE_PROPOSAL: create_proportional_dailyplan_calorie_proposal_tool,
        TOOL_PREPARE_PRODUCT_ACTION: prepare_product_action_tool,
        TOOL_CREATE_VALIDATED_MEAL_PROPOSAL: create_validated_meal_proposal_tool,
        TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL: create_nutrition_solver_meal_proposal_tool,
        TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL: create_validated_dailyplan_proposal_tool,
        TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL: create_validated_dailyplan_build_proposal_tool,
        TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: create_nutrition_engine_dailyplan_proposal_tool,
        TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS: create_nutrition_engine_dailyplan_proposal_from_drafts_tool,
        TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: iterate_nutrition_engine_dailyplan_proposal_tool,
    }


def execute_reviewable_proposal_tool(
    request: AssistantToolRequest,
    *,
    user: Any,
    executor: ReviewableProposalToolExecutor | None = None,
) -> AssistantToolResult:
    """Convenience function for one-shot reviewable proposal tool execution."""

    return (executor or ReviewableProposalToolExecutor()).execute(request, user=user)


def _extract_proposal_ids(value: Any) -> tuple[int, ...]:
    proposal_ids: list[int] = []

    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            raw_id = item.get("proposal_id") or item.get("id") if _looks_like_proposal_mapping(item) else item.get("proposal_id")
            if raw_id is not None:
                try:
                    proposal_id = int(raw_id)
                except (TypeError, ValueError):
                    proposal_id = 0
                if proposal_id > 0 and proposal_id not in proposal_ids:
                    proposal_ids.append(proposal_id)
            for key, nested in item.items():
                if str(key) in {"proposal", "source_proposal", "generated_proposal"} or isinstance(nested, Mapping | list | tuple):
                    visit(nested)
        elif isinstance(item, list | tuple):
            for nested in item:
                visit(nested)

    visit(value or {})
    return tuple(proposal_ids)


def _looks_like_proposal_mapping(value: Mapping[str, Any]) -> bool:
    keys = set(str(key) for key in value.keys())
    return bool({"proposal_type", "validation_summary", "status", "source"} & keys)


def _blocked_result(
    request: AssistantToolRequest,
    *,
    error_code: str,
    error_message: str,
    details: dict[str, Any] | None = None,
) -> AssistantToolResult:
    metadata = {
        "executor": "reviewable_proposal_tool_executor.v1",
        "writes_allowed": False,
        "applies_changes": False,
        "creates_reviewable_proposal": False,
    }
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


def _error_result(
    request: AssistantToolRequest,
    *,
    error_code: str,
    error_message: str,
    details: dict[str, Any] | None = None,
) -> AssistantToolResult:
    metadata = {
        "executor": "reviewable_proposal_tool_executor.v1",
        "writes_allowed": False,
        "applies_changes": False,
        "creates_reviewable_proposal": False,
    }
    if details:
        metadata["details"] = details
    return AssistantToolResult(
        tool_name=request.tool_name,
        status=AssistantToolStatus.ERROR,
        request_id=request.request_id,
        error_code=error_code,
        error_message=error_message,
        metadata=metadata,
    )
