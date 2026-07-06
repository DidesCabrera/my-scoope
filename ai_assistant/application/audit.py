from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ai_assistant.domain import (
    AssistantStructuredResponse,
    AssistantToolRequest,
    AssistantToolResult,
)

AUDIT_SCHEMA_VERSION = "ai_assistant_turn_audit.v1"

SENSITIVE_AUDIT_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "client_secret",
    "cookie",
    "headers",
    "input",
    "messages",
    "password",
    "payload",
    "prompt",
    "raw",
    "refresh_token",
    "request",
    "response",
    "secret",
    "set_cookie",
}

MAX_AUDIT_STRING_LENGTH = 240
MAX_AUDIT_SEQUENCE_LENGTH = 20
MAX_AUDIT_MAPPING_LENGTH = 30


@dataclass(frozen=True)
class AssistantToolAuditItem:
    """Sanitized audit representation of one requested AI Assistant tool."""

    tool_name: str
    status: str
    request_id: str = ""
    error_code: str = ""
    category: str = ""
    risk_level: str = ""
    requires_human_review: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tool_name": self.tool_name,
            "status": self.status,
        }
        if self.request_id:
            payload["request_id"] = self.request_id
        if self.error_code:
            payload["error_code"] = self.error_code
        if self.category:
            payload["category"] = self.category
        if self.risk_level:
            payload["risk_level"] = self.risk_level
        if self.requires_human_review is not None:
            payload["requires_human_review"] = self.requires_human_review
        return payload


@dataclass(frozen=True)
class AssistantTurnAuditSnapshot:
    """Sanitized trace for one AI Assistant turn.

    This object is intentionally compact: it records operational observability
    and safety decisions, but it does not persist prompts, provider payloads,
    request arguments, raw responses, headers or secrets.
    """

    version: str = AUDIT_SCHEMA_VERSION
    engine: str = ""
    provider: str = ""
    provider_model: str = ""
    provider_response_id: str = ""
    provider_usage: Mapping[str, Any] = field(default_factory=dict)
    latency_ms: int | None = None
    tool_requests_count: int = 0
    tool_results_count: int = 0
    tool_requests_blocked: int = 0
    tools_executed: bool = False
    tool_audit: Sequence[AssistantToolAuditItem] = field(default_factory=tuple)
    proposal_ids: Sequence[int] = field(default_factory=tuple)
    requires_human_review: bool = True
    safety_flags: Sequence[str] = field(default_factory=tuple)
    error_code: str = ""
    error_type: str = ""
    provider_parse_error: str = ""
    provider_response_was_json: bool | None = None
    ignored_provider_proposal_ids_count: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "version": self.version,
            "engine": self.engine,
            "provider": self.provider,
            "provider_model": self.provider_model,
            "tool_requests_count": self.tool_requests_count,
            "tool_results_count": self.tool_results_count,
            "tool_requests_blocked": self.tool_requests_blocked,
            "tools_executed": self.tools_executed,
            "tool_audit": [item.as_dict() for item in self.tool_audit],
            "proposal_ids": list(self.proposal_ids),
            "requires_human_review": self.requires_human_review,
            "safety_flags": list(self.safety_flags),
            "ignored_provider_proposal_ids_count": self.ignored_provider_proposal_ids_count,
        }
        if self.provider_response_id:
            payload["provider_response_id"] = self.provider_response_id
        if self.provider_usage:
            payload["provider_usage"] = sanitize_audit_value(self.provider_usage)
        if self.latency_ms is not None:
            payload["latency_ms"] = self.latency_ms
        if self.error_code:
            payload["error_code"] = self.error_code
        if self.error_type:
            payload["error_type"] = self.error_type
        if self.provider_parse_error:
            payload["provider_parse_error"] = self.provider_parse_error
        if self.provider_response_was_json is not None:
            payload["provider_response_was_json"] = self.provider_response_was_json
        if self.metadata:
            payload["metadata"] = sanitize_audit_value(self.metadata)
        return payload


def build_audit_snapshot(
    *,
    response: AssistantStructuredResponse | None = None,
    engine: str = "",
    provider: str = "",
    provider_model: str = "",
    provider_response_id: str = "",
    provider_usage: Mapping[str, Any] | None = None,
    latency_ms: int | None = None,
    tools_executed: bool = False,
    proposal_ids: Sequence[int] | None = None,
    error_code: str = "",
    error_type: str = "",
    provider_parse_error: str = "",
    provider_response_was_json: bool | None = None,
    ignored_provider_proposal_ids: Sequence[Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AssistantTurnAuditSnapshot:
    """Build a compact, sanitized audit snapshot for a single assistant turn."""

    response_metadata = dict(response.metadata or {}) if response else {}
    tool_requests = tuple(response.tool_requests or ()) if response else ()
    tool_results = tuple(response.tool_results or ()) if response else ()
    requested_proposal_ids = tuple(int(value) for value in (proposal_ids or ()))
    if not requested_proposal_ids and response:
        requested_proposal_ids = tuple(response.proposal_ids or ())

    blocked_results = [result for result in tool_results if result.status.value == "blocked"]

    return AssistantTurnAuditSnapshot(
        engine=engine or str(response_metadata.get("engine") or ""),
        provider=provider or str(response_metadata.get("provider") or ""),
        provider_model=provider_model or str(response_metadata.get("provider_model") or ""),
        provider_response_id=provider_response_id or str(response_metadata.get("provider_response_id") or ""),
        provider_usage=provider_usage or response_metadata.get("provider_usage") or {},
        latency_ms=latency_ms,
        tool_requests_count=len(tool_requests),
        tool_results_count=len(tool_results),
        tool_requests_blocked=len(blocked_results),
        tools_executed=tools_executed,
        tool_audit=tuple(_build_tool_audit_items(tool_requests=tool_requests, tool_results=tool_results)),
        proposal_ids=requested_proposal_ids,
        requires_human_review=response.requires_human_review if response else True,
        safety_flags=tuple(response.intent.safety_flags if response else ()),
        error_code=error_code,
        error_type=error_type,
        provider_parse_error=provider_parse_error or str(response_metadata.get("provider_parse_error") or ""),
        provider_response_was_json=provider_response_was_json
        if provider_response_was_json is not None
        else response_metadata.get("provider_response_was_json"),
        ignored_provider_proposal_ids_count=len(tuple(ignored_provider_proposal_ids or ())),
        metadata=metadata or {},
    )


def sanitize_audit_value(value: Any, *, depth: int = 0) -> Any:
    """Return a JSON-safe value suitable for audit metadata.

    The sanitizer is deliberately conservative. It preserves small primitive
    metrics such as token counts while redacting prompts, payloads, headers and
    secrets before they can be written to logs or persisted metadata.
    """

    if depth > 4:
        return "[truncated]"
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for index, (key, nested_value) in enumerate(value.items()):
            if index >= MAX_AUDIT_MAPPING_LENGTH:
                sanitized["_truncated"] = True
                break
            key_text = str(key)
            normalized_key = _normalize_audit_key(key_text)
            if _is_sensitive_audit_key(normalized_key):
                sanitized[key_text] = "[redacted]"
            else:
                sanitized[key_text] = sanitize_audit_value(nested_value, depth=depth + 1)
        return sanitized
    if isinstance(value, list | tuple | set):
        sequence = list(value)
        sanitized_sequence = [sanitize_audit_value(item, depth=depth + 1) for item in sequence[:MAX_AUDIT_SEQUENCE_LENGTH]]
        if len(sequence) > MAX_AUDIT_SEQUENCE_LENGTH:
            sanitized_sequence.append("[truncated]")
        return sanitized_sequence
    if isinstance(value, str):
        return _truncate_audit_text(value)
    if value is None or isinstance(value, bool | int | float):
        return value
    return _truncate_audit_text(str(value))


def _build_tool_audit_items(
    *,
    tool_requests: Sequence[AssistantToolRequest],
    tool_results: Sequence[AssistantToolResult],
) -> list[AssistantToolAuditItem]:
    results_by_request_id = {result.request_id: result for result in tool_results if result.request_id}
    results_by_tool_name = {result.tool_name: result for result in tool_results}
    items: list[AssistantToolAuditItem] = []
    for request in tool_requests:
        result = results_by_request_id.get(request.request_id) or results_by_tool_name.get(request.tool_name)
        if result is None:
            items.append(
                AssistantToolAuditItem(
                    tool_name=request.tool_name,
                    status="requested",
                    request_id=request.request_id,
                )
            )
            continue
        data = dict(result.data or {})
        items.append(
            AssistantToolAuditItem(
                tool_name=result.tool_name,
                status=result.status.value,
                request_id=result.request_id,
                error_code=result.error_code,
                category=str(data.get("category") or ""),
                risk_level=str(data.get("risk_level") or ""),
                requires_human_review=data.get("requires_human_review") if "requires_human_review" in data else None,
            )
        )
    return items


def _normalize_audit_key(value: str) -> str:
    return "".join(ch for ch in value.lower().strip().replace("-", "_") if ch.isalnum() or ch == "_")


def _is_sensitive_audit_key(normalized_key: str) -> bool:
    if normalized_key in SENSITIVE_AUDIT_KEYS:
        return True
    return normalized_key.endswith("_api_key") or normalized_key.endswith("_secret") or normalized_key.endswith("_password")


def _truncate_audit_text(value: str) -> str:
    if len(value) <= MAX_AUDIT_STRING_LENGTH:
        return value
    return f"{value[:MAX_AUDIT_STRING_LENGTH]}…"
