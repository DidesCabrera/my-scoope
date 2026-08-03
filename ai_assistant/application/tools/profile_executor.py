from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ai_assistant.application.tools.contracts import AssistantToolCategory
from ai_assistant.application.tools.registry import (
    TOOL_SHARE_PREFERENCE_DRAFT_CARD,
    TOOL_SHARE_PROFILE_DRAFT_CARD,
    TOOL_SHARE_PROPOSAL_PREFERENCES_CARD,
    TOOL_UPDATE_PREFERENCE_DRAFT,
    TOOL_UPDATE_PROFILE_DRAFT,
    TOOL_UPDATE_PROPOSAL_PREFERENCES,
    get_tool_spec,
    normalize_tool_name,
    validate_tool_request,
)
from ai_assistant.domain.contracts import (
    AssistantToolRequest,
    AssistantToolResult,
    AssistantToolStatus,
)
from ai_assistant.domain.tool_results import AIToolResult

ProfileDraftToolCallable = Callable[..., AIToolResult]


@dataclass(frozen=True)
class ProfileDraftToolExecutor:
    """Execute non-persistent draft tools for the LLM assistant.

    Draft tools let the assistant fill structured objects from the user's own
    words. They never write to Profile, WeightLog or future preference stores;
    a later approval/commit tool must handle persistence.
    """

    dispatch_table: Mapping[str, ProfileDraftToolCallable] = field(default_factory=dict)

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
        if spec.category != AssistantToolCategory.DRAFT:
            return _blocked_result(
                normalized_request,
                error_code="non_draft_tool_blocked",
                error_message="This executor only runs non-persistent AI Assistant draft tools.",
                details={
                    "category": spec.category.value,
                    "risk_level": spec.risk_level.value,
                },
            )

        tool_fn = self._resolve_tool(normalized_request.tool_name)
        if tool_fn is None:
            return _blocked_result(
                normalized_request,
                error_code="draft_tool_not_dispatchable",
                error_message="This draft tool is not connected to the local executor.",
            )

        try:
            raw_result = tool_fn(user, **dict(normalized_request.arguments or {}))
        except TypeError as exc:
            return _error_result(
                normalized_request,
                error_code="draft_tool_argument_error",
                error_message="Draft tool arguments could not be dispatched safely.",
                details={"exception": exc.__class__.__name__},
            )

        if raw_result.ok:
            return AssistantToolResult(
                tool_name=normalized_request.tool_name,
                status=AssistantToolStatus.OK,
                request_id=normalized_request.request_id,
                data=dict(raw_result.data or {}),
                metadata={
                    "executor": "profile_draft_tool_executor.v1",
                    "category": spec.category.value,
                    "risk_level": spec.risk_level.value,
                    "writes_allowed": False,
                    "persistent_profile_updated": False,
                    "draft_only": True,
                    "requires_user_approval_for_persistence": True,
                },
            )

        error = raw_result.error
        return _error_result(
            normalized_request,
            error_code=error.code if error else "draft_tool_error",
            error_message=error.message if error else "Draft tool execution failed.",
            details=error.details if error else {},
        )

    def _resolve_tool(self, tool_name: str) -> ProfileDraftToolCallable | None:
        dispatch_table = dict(self.dispatch_table or {})
        if not dispatch_table:
            dispatch_table = build_default_profile_draft_tool_dispatch_table()
        return dispatch_table.get(normalize_tool_name(tool_name))


def build_default_profile_draft_tool_dispatch_table() -> dict[str, ProfileDraftToolCallable]:
    """Load registered product draft tools lazily."""

    from ai_assistant.application.product_ports import get_ai_product_bindings

    return dict(get_ai_product_bindings().profile_draft_tools)


def execute_profile_draft_tool(
    request: AssistantToolRequest,
    *,
    user: Any,
    executor: ProfileDraftToolExecutor | None = None,
) -> AssistantToolResult:
    """Convenience function for one-shot profile draft tool execution."""

    return (executor or ProfileDraftToolExecutor()).execute(request, user=user)


def _blocked_result(
    request: AssistantToolRequest,
    *,
    error_code: str,
    error_message: str,
    details: dict[str, Any] | None = None,
) -> AssistantToolResult:
    metadata = {
        "executor": "profile_draft_tool_executor.v1",
        "writes_allowed": False,
        "persistent_profile_updated": False,
        "draft_only": True,
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
        "executor": "profile_draft_tool_executor.v1",
        "writes_allowed": False,
        "persistent_profile_updated": False,
        "draft_only": True,
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
