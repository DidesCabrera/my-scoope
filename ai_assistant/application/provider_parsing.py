from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ai_assistant.domain import (
    AssistantContractError,
    AssistantIntent,
    AssistantIntentName,
    AssistantMessage,
    AssistantMessageRole,
    AssistantStructuredResponse,
    AssistantToolRequest,
)

@dataclass(frozen=True)
class AssistantProviderParseResult:
    """Result of normalizing provider text into an internal structured response."""

    response: AssistantStructuredResponse
    was_json: bool
    parse_error: str = ""
    ignored_provider_proposal_ids: Sequence[Any] = field(default_factory=tuple)
    declared_tools_required: bool = False


def _loads_json_object(text: str) -> tuple[dict[str, Any] | None, str]:
    if not text:
        return None, "empty_provider_response"
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = _strip_code_fence(cleaned)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return None, f"invalid_json:{exc.msg}"
    if not isinstance(payload, dict):
        return None, "json_root_must_be_object"
    return payload, ""


def _strip_code_fence(text: str) -> str:
    lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
    return "\n".join(lines).strip()


def _extract_jsonish_assistant_content(text: str) -> str:
    """Best-effort extraction for malformed provider JSON.

    The visible chat should never show the full structured payload just because
    the provider returned a near-JSON object with a small syntax issue, such as
    a trailing comma. This fallback only extracts the display text and leaves the
    turn marked as non-JSON for audit/observability.
    """

    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    if cleaned.startswith("```"):
        cleaned = _strip_code_fence(cleaned)

    for field_name in ("content", "assistant_text", "message"):
        value = _extract_jsonish_string_field(cleaned, field_name)
        if value:
            return value
    return ""


def _extract_jsonish_string_field(text: str, field_name: str) -> str:
    marker = f'"{field_name}"'
    field_index = text.find(marker)
    if field_index < 0:
        return ""
    colon_index = text.find(":", field_index + len(marker))
    if colon_index < 0:
        return ""

    candidate = text[colon_index + 1 :].lstrip()
    if not candidate.startswith('"'):
        return ""

    try:
        value, _ = json.JSONDecoder().raw_decode(candidate)
    except json.JSONDecodeError:
        return ""
    if not isinstance(value, str):
        return ""
    return value.strip()


def _loads_json_mapping(value: Any, *, field_name: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    try:
        parsed = json.loads(str(value or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AssistantContractError(f"{field_name} must contain a valid JSON object string.") from exc
    if not isinstance(parsed, Mapping):
        raise AssistantContractError(f"{field_name} must contain a JSON object.")
    return dict(parsed)


def _coerce_assistant_message(payload: Mapping[str, Any]) -> AssistantMessage:
    assistant_message = payload.get("assistant_message")
    if isinstance(assistant_message, Mapping):
        content = assistant_message.get("content") or assistant_message.get("text") or ""
    else:
        content = assistant_message or payload.get("assistant_text") or payload.get("message") or ""
    return AssistantMessage(role=AssistantMessageRole.ASSISTANT, content=str(content or ""))


def _coerce_intent(value: Any) -> AssistantIntent:
    if not isinstance(value, Mapping):
        return AssistantIntent(name=AssistantIntentName.UNKNOWN, confidence=0.0)
    slots = value.get("slots")
    if slots is None and "slots_json" in value:
        slots = _loads_json_mapping(value.get("slots_json"), field_name="intent.slots_json")
    return AssistantIntent(
        name=value.get("name") or AssistantIntentName.UNKNOWN,
        confidence=value.get("confidence") or 0.0,
        summary=value.get("summary") or "",
        slots=slots or {},
        missing_slots=value.get("missing_slots") or (),
        safety_flags=value.get("safety_flags") or (),
    )


def _coerce_tool_requests(value: Any) -> tuple[AssistantToolRequest, ...]:
    if not value:
        return ()
    if not isinstance(value, list | tuple):
        raise AssistantContractError("tool_requests must be a list.")

    requests: list[AssistantToolRequest] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            raise AssistantContractError("Each tool request must be an object.")
        arguments = item.get("arguments")
        if arguments is None and "arguments_json" in item:
            arguments = _loads_json_mapping(
                item.get("arguments_json"),
                field_name=f"tool_requests[{index}].arguments_json",
            )
        requests.append(
            AssistantToolRequest(
                tool_name=item.get("tool_name") or item.get("name") or "",
                arguments=arguments or {},
                request_id=item.get("request_id") or f"tool_request_{index}",
                reason=item.get("reason") or "",
            )
        )
    return tuple(requests)


def _coerce_requires_human_review(payload: Mapping[str, Any]) -> bool:
    value = payload.get("requires_human_review")
    if value is None:
        return True
    return bool(value)
