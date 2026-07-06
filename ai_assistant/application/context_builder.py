from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ai_assistant.application.chat_engines import ChatEngineRequest

MAX_TEXT_LENGTH = 240
MAX_LIST_ITEMS = 8
MAX_CONTEXT_DEPTH = 3

SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "csrf",
    "email",
    "header",
    "password",
    "phone",
    "secret",
    "token",
)

NUTRITION_BRIEF_FIELDS = (
    "goal",
    "requested_entity",
    "meals_per_day",
    "training_frequency",
    "calorie_target",
    "protein_target",
    "carb_target",
    "fat_target",
    "weight_kg",
    "height_cm",
    "age_years",
    "sex",
    "activity_level",
    "energy_adjustment",
    "style_preferences",
    "excluded_foods",
    "preferred_foods",
    "complexity_level",
    "budget_level",
    "notes",
)


@dataclass(frozen=True)
class SafeLLMContext:
    """Small structured context payload that may be sent to an external LLM.

    The context is intentionally provider-facing, bounded and serializable. It
    must not contain Django model instances, request objects, raw session
    payloads, headers, API keys, emails, tokens or full tool arguments.
    """

    surface: str
    user: Mapping[str, Any]
    conversation: Mapping[str, Any]
    nutrition_brief: Mapping[str, Any] = field(default_factory=dict)
    runtime: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "surface": self.surface,
            "user": dict(self.user),
            "conversation": dict(self.conversation),
            "runtime": dict(self.runtime),
        }
        if self.nutrition_brief:
            payload["nutrition_brief"] = dict(self.nutrition_brief)
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


def build_safe_llm_context(
    request: ChatEngineRequest,
    *,
    surface: str = "ai_nutrition_intake",
    conversation_state: Any | None = None,
    extra_context: Mapping[str, Any] | None = None,
) -> SafeLLMContext:
    """Build the minimal provider-facing context for an LLM chat turn."""

    safe_extra = _sanitize_mapping(extra_context or {})
    nutrition_brief = _extract_nutrition_brief(conversation_state)
    conversation_context = _conversation_context(
        request=request,
        conversation_state=conversation_state,
    )
    return SafeLLMContext(
        surface=_bounded_text(surface),
        user={
            "authenticated": request.user_id is not None,
            "id_present": request.user_id is not None,
        },
        conversation=conversation_context,
        nutrition_brief=nutrition_brief,
        runtime={
            "tools_enabled": False,
            "tool_execution_stage": "none",
            "proposal_creation_enabled": False,
            "human_review_required": True,
        },
        metadata={
            "context_builder": "safe_llm_context.v1",
            "extra_context_keys": sorted(safe_extra.keys()),
            **safe_extra,
        },
    )


def merge_safe_context_into_request(
    request: ChatEngineRequest,
    *,
    safe_context: SafeLLMContext,
) -> ChatEngineRequest:
    """Return a new chat request carrying only safe LLM context in metadata."""

    metadata = dict(request.metadata or {})
    metadata["safe_llm_context"] = safe_context.as_dict()
    metadata["safe_llm_context_version"] = "safe_llm_context.v1"
    return ChatEngineRequest(
        message=request.message,
        existing_payload=request.existing_payload,
        user_id=request.user_id,
        metadata=metadata,
    )


def _conversation_context(
    *,
    request: ChatEngineRequest,
    conversation_state: Any | None,
) -> dict[str, Any]:
    messages = list(getattr(conversation_state, "messages", []) or [])
    required_questions = list(getattr(conversation_state, "required_follow_up_questions", []) or [])
    visible_questions = list(getattr(conversation_state, "visible_follow_up_questions", []) or [])
    return {
        "existing_payload_present": request.existing_payload is not None,
        "message_count": len(messages),
        "last_assistant_present": bool(getattr(conversation_state, "last_assistant_message", "")),
        "is_ready_for_proposal": bool(getattr(conversation_state, "is_ready_for_proposal", False)),
        "required_follow_up_questions_count": len(required_questions),
        "visible_follow_up_questions": [_bounded_text(item) for item in visible_questions[:MAX_LIST_ITEMS]],
    }


def _extract_nutrition_brief(conversation_state: Any | None) -> dict[str, Any]:
    result = getattr(conversation_state, "result", None)
    brief = getattr(result, "brief", None)
    if brief is None:
        return {}

    payload: dict[str, Any] = {}
    for field_name in NUTRITION_BRIEF_FIELDS:
        value = getattr(brief, field_name, None)
        if _has_value(value):
            payload[field_name] = _sanitize_value(value)
    payload["is_ready_for_proposal"] = bool(getattr(result, "is_ready_for_proposal", False))
    payload["has_pending_questions"] = bool(getattr(result, "has_pending_questions", False))
    payload["has_required_pending_questions"] = bool(getattr(result, "has_required_pending_questions", False))
    return payload


def sanitize_provider_context(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return a bounded, provider-safe copy of an arbitrary context mapping."""

    return _sanitize_mapping(value or {})


def _sanitize_mapping(value: Mapping[str, Any], *, depth: int = 0) -> dict[str, Any]:
    if depth >= MAX_CONTEXT_DEPTH:
        return {"truncated": True}

    safe: dict[str, Any] = {}
    for key, item in value.items():
        key_text = _safe_key(key)
        if not key_text or _is_sensitive_key(key_text):
            continue
        safe[key_text] = _sanitize_value(item, depth=depth + 1)
    return safe


def _sanitize_value(value: Any, *, depth: int = 0) -> Any:
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _bounded_text(value)
    if isinstance(value, Mapping):
        return _sanitize_mapping(value, depth=depth)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_sanitize_value(item, depth=depth + 1) for item in list(value)[:MAX_LIST_ITEMS]]
    return _bounded_text(value.__class__.__name__)


def _safe_key(value: Any) -> str:
    return "_".join(str(value or "").strip().lower().split())[:64]


def _is_sensitive_key(key: str) -> bool:
    return any(fragment in key for fragment in SENSITIVE_KEY_FRAGMENTS)


def _bounded_text(value: Any) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= MAX_TEXT_LENGTH:
        return text
    return f"{text[:MAX_TEXT_LENGTH]}…"


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return bool(value)
    return True
