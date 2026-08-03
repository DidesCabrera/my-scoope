from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ai_assistant.application.tools.contracts import AssistantToolCategory
from ai_assistant.application.tools.registry import (
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
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

ValidationToolCallable = Callable[..., AIToolResult]


@dataclass(frozen=True)
class ValidationToolExecutor:
    """Execute validation/comparison tools without mutating product data."""

    dispatch_table: Mapping[str, ValidationToolCallable] = field(default_factory=dict)

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
        if spec.category != AssistantToolCategory.VALIDATION:
            return _blocked_result(
                normalized_request,
                error_code="non_validation_tool_blocked",
                error_message="This executor only runs validation AI Assistant tools.",
                details={
                    "category": spec.category.value,
                    "risk_level": spec.risk_level.value,
                },
            )

        tool_fn = self._resolve_tool(normalized_request.tool_name)
        if tool_fn is None:
            return _blocked_result(
                normalized_request,
                error_code="validation_tool_not_dispatchable",
                error_message="This validation tool is not connected to the local executor.",
            )

        try:
            raw_result = tool_fn(user, **dict(normalized_request.arguments or {}))
        except TypeError as exc:
            return _error_result(
                normalized_request,
                error_code="validation_tool_argument_error",
                error_message="Validation tool arguments could not be dispatched safely.",
                details={"exception": exc.__class__.__name__},
            )

        if raw_result.ok:
            return AssistantToolResult(
                tool_name=normalized_request.tool_name,
                status=AssistantToolStatus.OK,
                request_id=normalized_request.request_id,
                data=dict(raw_result.data or {}),
                metadata={
                    "executor": "validation_tool_executor.v1",
                    "category": spec.category.value,
                    "risk_level": spec.risk_level.value,
                    "writes_allowed": False,
                    "applies_changes": False,
                    "validation_only": True,
                },
            )

        error = raw_result.error
        return _error_result(
            normalized_request,
            error_code=error.code if error else "validation_tool_error",
            error_message=error.message if error else "Validation tool execution failed.",
            details=error.details if error else {},
        )

    def _resolve_tool(self, tool_name: str) -> ValidationToolCallable | None:
        dispatch_table = dict(self.dispatch_table or {})
        if not dispatch_table:
            dispatch_table = build_default_validation_tool_dispatch_table()
        return dispatch_table.get(normalize_tool_name(tool_name))


def build_default_validation_tool_dispatch_table() -> dict[str, ValidationToolCallable]:
    """Load registered validation tool dispatchers lazily."""

    from ai_assistant.application.product_ports import get_ai_product_bindings

    return dict(get_ai_product_bindings().validation_tools)


def execute_validation_tool(
    request: AssistantToolRequest,
    *,
    user: Any,
    executor: ValidationToolExecutor | None = None,
) -> AssistantToolResult:
    """Convenience function for one-shot validation tool execution."""

    return (executor or ValidationToolExecutor()).execute(request, user=user)


def _blocked_result(
    request: AssistantToolRequest,
    *,
    error_code: str,
    error_message: str,
    details: dict[str, Any] | None = None,
) -> AssistantToolResult:
    metadata = {
        "executor": "validation_tool_executor.v1",
        "writes_allowed": False,
        "applies_changes": False,
        "validation_only": True,
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
        "executor": "validation_tool_executor.v1",
        "writes_allowed": False,
        "applies_changes": False,
        "validation_only": True,
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
