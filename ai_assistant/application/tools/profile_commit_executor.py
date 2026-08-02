from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ai_assistant.application.tools.contracts import AssistantToolCategory
from ai_assistant.application.tools.registry import (
    TOOL_COMMIT_PROFILE_UPDATE,
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

ProfileCommitToolCallable = Callable[..., AIToolResult]

TRUSTED_APPROVAL_SOURCES = {
    "profile_card_button",
    "system_approved_profile_card",
}


@dataclass(frozen=True)
class ProfileCommitToolExecutor:
    """Execute explicit user-approved profile commit tools.

    Commit tools are internal My Scoope actions. They are not exposed as provider
    tools and they require trusted server-side approval metadata before any
    persistent profile write may happen.
    """

    dispatch_table: Mapping[str, ProfileCommitToolCallable] = field(default_factory=dict)

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
            metadata=dict(request.metadata or {}),
        )
        validation_result = validate_tool_request(normalized_request)
        if validation_result.status != AssistantToolStatus.PENDING:
            return validation_result

        spec = get_tool_spec(normalized_request.tool_name)
        if spec.category != AssistantToolCategory.COMMIT:
            return _blocked_result(
                normalized_request,
                error_code="non_profile_commit_tool_blocked",
                error_message="This executor only runs approved profile commit tools.",
                details={"category": spec.category.value, "risk_level": spec.risk_level.value},
            )

        if not _has_trusted_user_approval(normalized_request):
            return _blocked_result(
                normalized_request,
                error_code="profile_commit_requires_trusted_user_approval",
                error_message="Profile commit tools require a trusted server-side user approval event.",
            )

        tool_fn = self._resolve_tool(normalized_request.tool_name)
        if tool_fn is None:
            return _blocked_result(
                normalized_request,
                error_code="profile_commit_tool_not_dispatchable",
                error_message="This profile commit tool is not connected to the local executor.",
            )

        try:
            raw_result = tool_fn(user, **dict(normalized_request.arguments or {}))
        except TypeError as exc:
            return _error_result(
                normalized_request,
                error_code="profile_commit_tool_argument_error",
                error_message="Profile commit tool arguments could not be dispatched safely.",
                details={"exception": exc.__class__.__name__},
            )

        if raw_result.ok:
            data = dict(raw_result.data or {})
            source_boundary = dict(data.get("source_boundary") or {})
            return AssistantToolResult(
                tool_name=normalized_request.tool_name,
                status=AssistantToolStatus.OK,
                request_id=normalized_request.request_id,
                data=data,
                metadata={
                    "executor": "profile_commit_tool_executor.v1",
                    "category": spec.category.value,
                    "risk_level": spec.risk_level.value,
                    "writes_allowed": True,
                    "persistent_profile_updated": bool(source_boundary.get("persistent_profile_updated")),
                    "requires_user_approval": True,
                    "trusted_user_approval": True,
                    "approval_source": normalized_request.metadata.get("approval_source"),
                },
            )

        error = raw_result.error
        return _error_result(
            normalized_request,
            error_code=error.code if error else "profile_commit_tool_error",
            error_message=error.message if error else "Profile commit tool execution failed.",
            details=error.details if error else {},
        )

    def _resolve_tool(self, tool_name: str) -> ProfileCommitToolCallable | None:
        dispatch_table = dict(self.dispatch_table or {})
        if not dispatch_table:
            dispatch_table = build_default_profile_commit_tool_dispatch_table()
        return dispatch_table.get(normalize_tool_name(tool_name))


def build_default_profile_commit_tool_dispatch_table() -> dict[str, ProfileCommitToolCallable]:
    """Load local profile commit tools lazily."""

    from notas.application.ai_tools.profile_tools import commit_profile_update_tool

    return {
        TOOL_COMMIT_PROFILE_UPDATE: commit_profile_update_tool,
    }


def execute_profile_commit_tool(
    request: AssistantToolRequest,
    *,
    user: Any,
    executor: ProfileCommitToolExecutor | None = None,
) -> AssistantToolResult:
    """Convenience function for one-shot approved profile commit execution."""

    return (executor or ProfileCommitToolExecutor()).execute(request, user=user)


def _has_trusted_user_approval(request: AssistantToolRequest) -> bool:
    metadata = dict(request.metadata or {})
    return (
        metadata.get("approved_by_user") is True
        and metadata.get("approval_source") in TRUSTED_APPROVAL_SOURCES
    )


def _blocked_result(
    request: AssistantToolRequest,
    *,
    error_code: str,
    error_message: str,
    details: dict[str, Any] | None = None,
) -> AssistantToolResult:
    metadata = {
        "executor": "profile_commit_tool_executor.v1",
        "writes_allowed": False,
        "persistent_profile_updated": False,
        "requires_user_approval": True,
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
        "executor": "profile_commit_tool_executor.v1",
        "writes_allowed": False,
        "persistent_profile_updated": False,
        "requires_user_approval": True,
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
