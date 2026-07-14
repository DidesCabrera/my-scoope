from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ai_assistant.application.tools.contracts import AssistantToolCategory
from ai_assistant.application.tools.registry import (
    TOOL_LIST_OPERATIONAL_FOODS,
    TOOL_LIST_SAVED_COMPARISONS,
    TOOL_LIST_USER_PROPOSALS,
    TOOL_READ_DAILYPLAN,
    TOOL_READ_SAVED_COMPARISON,
    TOOL_READ_USER_PROFILE_CONTEXT,
    TOOL_READ_PROPOSAL,
    TOOL_SEARCH_OPERATIONAL_FOODS,
    TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES,
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

ReadOnlyToolCallable = Callable[..., AIToolResult]

DEFAULT_TOOL_RESULT_LIMIT = 20
MAX_TOOL_RESULT_LIMIT = 50


@dataclass(frozen=True)
class ReadOnlyToolExecutorConfig:
    """Runtime limits for the read-only AI Assistant tool executor."""

    default_limit: int = DEFAULT_TOOL_RESULT_LIMIT
    max_limit: int = MAX_TOOL_RESULT_LIMIT


@dataclass(frozen=True)
class ReadOnlyToolExecutor:
    """Execute only allowlisted read-only AI Assistant tools.

    The executor is the first bridge between the provider-facing tool registry
    and My Scoope application services. It deliberately refuses validation,
    proposal and write-like tools. Patch 54 can compose this executor inside
    the LLM loop; this patch only provides the safe dispatch boundary.
    """

    dispatch_table: Mapping[str, ReadOnlyToolCallable] = field(default_factory=dict)
    config: ReadOnlyToolExecutorConfig = field(default_factory=ReadOnlyToolExecutorConfig)

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
        if spec.category != AssistantToolCategory.READ:
            return _blocked_result(
                normalized_request,
                error_code="non_read_only_tool_blocked",
                error_message="Patch 53 only executes read-only AI Assistant tools.",
                details={
                    "category": spec.category.value,
                    "risk_level": spec.risk_level.value,
                },
            )

        tool_fn = self._resolve_tool(normalized_request.tool_name)
        if tool_fn is None:
            return _blocked_result(
                normalized_request,
                error_code="read_only_tool_not_dispatchable",
                error_message="This read-only tool is not connected to the local executor.",
            )

        arguments = self._normalized_arguments(normalized_request.tool_name, normalized_request.arguments)
        try:
            raw_result = tool_fn(user, **arguments)
        except TypeError as exc:
            return _error_result(
                normalized_request,
                error_code="read_only_tool_argument_error",
                error_message="Read-only tool arguments could not be dispatched safely.",
                details={"exception": exc.__class__.__name__},
            )

        if raw_result.ok:
            return AssistantToolResult(
                tool_name=normalized_request.tool_name,
                status=AssistantToolStatus.OK,
                request_id=normalized_request.request_id,
                data=_limit_tool_data(
                    raw_result.data,
                    limit=arguments.get("limit", self.config.default_limit),
                ),
                metadata={
                    "executor": "read_only_tool_executor.v1",
                    "category": spec.category.value,
                    "risk_level": spec.risk_level.value,
                    "writes_allowed": False,
                },
            )

        error = raw_result.error
        return _error_result(
            normalized_request,
            error_code=error.code if error else "read_only_tool_error",
            error_message=error.message if error else "Read-only tool execution failed.",
            details=error.details if error else {},
        )

    def _resolve_tool(self, tool_name: str) -> ReadOnlyToolCallable | None:
        dispatch_table = dict(self.dispatch_table or {})
        if not dispatch_table:
            dispatch_table = build_default_read_only_tool_dispatch_table()
        return dispatch_table.get(normalize_tool_name(tool_name))

    def _normalized_arguments(self, tool_name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(arguments or {})
        limit = _coerce_limit(
            payload.pop("limit", self.config.default_limit),
            default=self.config.default_limit,
            maximum=self.config.max_limit,
        )

        if tool_name in {
            TOOL_LIST_OPERATIONAL_FOODS,
            TOOL_LIST_SAVED_COMPARISONS,
            TOOL_SEARCH_OPERATIONAL_FOODS,
            TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES,
        }:
            payload["limit"] = limit

        if tool_name == TOOL_SEARCH_OPERATIONAL_FOODS:
            payload["query"] = str(payload.get("query") or "").strip()

        if tool_name == TOOL_LIST_SAVED_COMPARISONS:
            payload["kind"] = str(payload.get("kind") or "").strip().lower() or None

        if tool_name == TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES:
            payload["search"] = str(payload.get("search") or "").strip() or None
            payload["include_extended"] = _coerce_bool(
                payload.get("include_extended", True),
                default=True,
            )

        return payload


def build_default_read_only_tool_dispatch_table() -> dict[str, ReadOnlyToolCallable]:
    """Load the local read-only tool dispatch table lazily.

    Importing `notas` happens here instead of in the registry, so the allowlist
    remains a pure provider-agnostic contract while the executor owns the local
    application-service dependency.
    """

    from notas.application.ai_tools.comparison_tools import (
        list_saved_comparisons_tool,
        read_saved_comparison_tool,
    )
    from notas.application.ai_tools.profile_tools import read_user_profile_context_tool
    from notas.application.ai_tools.read_tools import (
        list_available_foods_tool,
        list_user_proposals_tool,
        preview_nutrition_solver_candidates_tool,
        read_dailyplan_tool,
        read_proposal_tool,
        search_foods_tool,
    )

    return {
        TOOL_READ_DAILYPLAN: read_dailyplan_tool,
        TOOL_READ_PROPOSAL: read_proposal_tool,
        TOOL_LIST_SAVED_COMPARISONS: list_saved_comparisons_tool,
        TOOL_READ_SAVED_COMPARISON: read_saved_comparison_tool,
        TOOL_LIST_USER_PROPOSALS: list_user_proposals_tool,
        TOOL_READ_USER_PROFILE_CONTEXT: read_user_profile_context_tool,
        TOOL_SEARCH_OPERATIONAL_FOODS: _search_operational_foods_adapter(search_foods_tool),
        TOOL_LIST_OPERATIONAL_FOODS: _list_operational_foods_adapter(list_available_foods_tool),
        TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES: preview_nutrition_solver_candidates_tool,
    }


def execute_read_only_tool(
    request: AssistantToolRequest,
    *,
    user: Any,
    executor: ReadOnlyToolExecutor | None = None,
) -> AssistantToolResult:
    """Convenience function for one-shot read-only tool execution."""

    return (executor or ReadOnlyToolExecutor()).execute(request, user=user)


def _search_operational_foods_adapter(tool_fn: ReadOnlyToolCallable) -> ReadOnlyToolCallable:
    def wrapped(user: Any, *, query: str, limit: int = DEFAULT_TOOL_RESULT_LIMIT) -> AIToolResult:
        result = tool_fn(user, query=query)
        return _with_limited_collection(result, key="foods", limit=limit)

    return wrapped


def _list_operational_foods_adapter(tool_fn: ReadOnlyToolCallable) -> ReadOnlyToolCallable:
    def wrapped(user: Any, *, limit: int = DEFAULT_TOOL_RESULT_LIMIT) -> AIToolResult:
        result = tool_fn(user)
        return _with_limited_collection(result, key="foods", limit=limit)

    return wrapped


def _with_limited_collection(result: AIToolResult, *, key: str, limit: int) -> AIToolResult:
    if not result.ok:
        return result
    data = dict(result.data or {})
    items = data.get(key)
    if isinstance(items, list):
        data[key] = items[:limit]
        data["limit"] = limit
        data["truncated"] = len(items) > limit
    return AIToolResult(ok=True, data=data, error=None)


def _limit_tool_data(data: Mapping[str, Any], *, limit: int) -> dict[str, Any]:
    payload = dict(data or {})
    for key, value in list(payload.items()):
        if isinstance(value, list):
            payload[key] = value[:limit]
            payload.setdefault("limit", limit)
            payload.setdefault("truncated", len(value) > limit)
    return payload


def _coerce_limit(value: Any, *, default: int, maximum: int) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = default
    if limit < 1:
        return 1
    return min(limit, maximum)


def _coerce_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _blocked_result(
    request: AssistantToolRequest,
    *,
    error_code: str,
    error_message: str,
    details: dict[str, Any] | None = None,
) -> AssistantToolResult:
    metadata = {
        "executor": "read_only_tool_executor.v1",
        "writes_allowed": False,
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
        "executor": "read_only_tool_executor.v1",
        "writes_allowed": False,
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
