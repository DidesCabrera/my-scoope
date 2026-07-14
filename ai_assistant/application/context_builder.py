from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from django.conf import settings

from ai_assistant.application.chat_engines import ChatEngineRequest

MAX_TEXT_LENGTH = 240
MAX_RECENT_MESSAGE_TEXT_LENGTH = 1000
MAX_LIST_ITEMS = 8
MAX_CONTEXT_DEPTH = 6

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

PROFILE_DRAFT_FIELDS = (
    "weight_kg",
    "height_cm",
    "age_years",
    "sex",
    "activity_level",
    "training_frequency",
)

PREFERENCE_DRAFT_FIELDS = (
    "excluded_foods",
    "preferred_foods",
    "style_preferences",
    "complexity_level",
    "budget_level",
    "meals_per_day",
    "notes",
)

PROPOSAL_PREFERENCE_FIELDS = (
    "goal",
    "requested_entity",
    "meals_per_day",
    "energy_adjustment",
    "calorie_target",
    "protein_target",
    "carb_target",
    "fat_target",
    "notes",
)

NUTRITION_BRIEF_FIELDS = (
    "subject_source",
    "ppk_weight_source",
    "requires_library_ppk_warning",
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
    "field_sources",
)

# Internal bookkeeping fields that remain in NutritionBrief but should not be
# framed as user-facing facts for the LLM. In particular, weight source/date
# questions made the assistant over-structure the flow; a weight provided in
# chat should be assumed current for the current proposal unless the user says
# otherwise.
PROVIDER_OMITTED_NUTRITION_BRIEF_FIELDS = {
    "ppk_weight_source",
}


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
    reviewable_proposal_tools_enabled = _reviewable_proposal_tools_enabled()
    tool_oriented_intake = (
        _tool_oriented_intake_context(
            nutrition_brief,
            conversation_state=conversation_state,
            proposal_creation_enabled=reviewable_proposal_tools_enabled,
        )
        if surface == "ai_nutrition_intake"
        else {}
    )
    provider_nutrition_brief = {} if tool_oriented_intake else nutrition_brief
    return SafeLLMContext(
        surface=_bounded_text(surface),
        user={
            "authenticated": request.user_id is not None,
            "id_present": request.user_id is not None,
        },
        conversation=conversation_context,
        nutrition_brief=provider_nutrition_brief,
        runtime={
            "tools_enabled": True,
            "tool_execution_stage": "controlled_llm_tool_loop",
            "assistant_role": "tool_oriented_operator",
            "draft_state_scope": "conversation",
            "card_presentation": "explicit_tool_only",
            "proposal_creation_enabled": reviewable_proposal_tools_enabled,
            "persistent_writes_require_approval": True,
        },
        metadata={
            "context_builder": "safe_llm_context.v1",
            **({"tool_oriented_intake": tool_oriented_intake} if tool_oriented_intake else {}),
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



def _reviewable_proposal_tools_enabled() -> bool:
    return bool(getattr(settings, "AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS", False))


def _tool_oriented_intake_context(
    nutrition_brief: Mapping[str, Any],
    *,
    conversation_state: Any | None = None,
    proposal_creation_enabled: bool = False,
) -> dict[str, Any]:
    """Expose current intake objects without reconstructing an interviewer.

    CM20 keeps only state and a small interpretation contract in provider
    context. Field meaning, normalization and tool selection live in the typed
    provider tool declarations instead of duplicated completeness policies or
    recommended conversational sequences.
    """

    current_drafts = {
        "profile_draft": _draft_payload_from_fields(nutrition_brief, PROFILE_DRAFT_FIELDS),
        "preference_draft": _preference_draft_payload(nutrition_brief),
        "proposal_preferences": _draft_payload_from_fields(
            nutrition_brief,
            PROPOSAL_PREFERENCE_FIELDS,
        ),
    }
    work_context = _draft_payload_from_fields(
        nutrition_brief,
        ("subject_source", "requires_library_ppk_warning"),
    )
    return {
        "version": "ai_assistant_tool_oriented_intake.v9",
        "assistant_role": "operator_assistant",
        "current_drafts": current_drafts,
        "work_progress": _work_progress_context(
            conversation_state,
            proposal_creation_enabled=proposal_creation_enabled,
        ),
        **({"work_context": work_context} if work_context else {}),
        "context_semantics": {
            "present_values_are_known_for_this_conversation": True,
            "absent_values_are_not_automatically_required": True,
            "new_facts_are_recorded_through_typed_tools": True,
            "readiness_is_product_state_not_a_question_order": True,
        },
    }


def _work_progress_context(
    conversation_state: Any | None,
    *,
    proposal_creation_enabled: bool,
) -> dict[str, Any]:
    """Expose product-computed readiness without selecting the next conversation step.

    The state builder already knows whether the minimum proposal contract is
    complete. BA04 makes that bounded state visible to the provider so the LLM
    can choose a useful next action. It does not provide question wording, a
    recommended sequence or a backend interpretation of the latest message.
    """

    result = getattr(conversation_state, "result", None)
    ready_for_proposal = bool(getattr(result, "is_ready_for_proposal", False))
    required_information_missing = bool(
        getattr(result, "has_required_pending_questions", False)
    )
    if ready_for_proposal:
        proposal_readiness = "ready_for_reviewable_proposal"
    elif required_information_missing:
        proposal_readiness = "requires_blocking_information"
    else:
        proposal_readiness = "not_established"

    return {
        "surface_objective": "reach_a_useful_my_scoope_outcome",
        "proposal_readiness": proposal_readiness,
        "reviewable_proposal_creation_available": bool(proposal_creation_enabled),
        "required_information_still_missing": required_information_missing,
        "optional_refinement_is_not_required": True,
        "next_action_is_selected_by_the_assistant": True,
    }


def _draft_payload_from_fields(source: Mapping[str, Any], fields: Sequence[str]) -> dict[str, Any]:
    draft: dict[str, Any] = {}
    source_map = source.get("field_sources") if isinstance(source.get("field_sources"), Mapping) else {}
    draft_source_map: dict[str, Any] = {}
    for field_name in fields:
        value = source.get(field_name)
        if _has_value(value):
            draft[field_name] = _sanitize_value(value)
            if source_map.get(field_name):
                draft_source_map[field_name] = _sanitize_value(source_map.get(field_name))
    if draft_source_map:
        draft["field_sources"] = draft_source_map
    return draft


def _preference_draft_payload(nutrition_brief: Mapping[str, Any]) -> dict[str, Any]:
    draft: dict[str, Any] = {}
    if _has_value(nutrition_brief.get("excluded_foods")):
        draft["avoided_foods"] = _sanitize_value(nutrition_brief.get("excluded_foods"))
    if _has_value(nutrition_brief.get("preferred_foods")):
        draft["preferred_foods"] = _sanitize_value(nutrition_brief.get("preferred_foods"))
    for field_name in ("style_preferences", "complexity_level", "budget_level", "meals_per_day", "notes"):
        value = nutrition_brief.get(field_name)
        if _has_value(value):
            draft[field_name] = _sanitize_value(value)
    return draft


def _conversation_context(
    *,
    request: ChatEngineRequest,
    conversation_state: Any | None,
) -> dict[str, Any]:
    messages = list(getattr(conversation_state, "messages", []) or [])
    recent_objects = _recent_chat_objects(messages)
    context = {
        "existing_payload_present": request.existing_payload is not None,
        "message_count": len(messages),
        "last_assistant_present": bool(getattr(conversation_state, "last_assistant_message", "")),
        "recent_messages": _recent_conversation_messages(messages),
        "recent_chat_objects": recent_objects,
        "last_shared_object": recent_objects[-1] if recent_objects else {},
    }
    return context


def _recent_conversation_messages(messages: Sequence[Any]) -> list[dict[str, str]]:
    recent = []
    for message in list(messages or ())[-12:]:
        role = _bounded_text(getattr(message, "role", ""))
        text = _bounded_text(
            getattr(message, "text", ""),
            max_chars=MAX_RECENT_MESSAGE_TEXT_LENGTH,
        )
        if role and text:
            recent.append({"role": role, "text": text})
    return recent


def _recent_chat_objects(messages: Sequence[Any]) -> list[dict[str, Any]]:
    """Summarize user-visible cards so the LLM can resolve references to them.

    Cards are stored as assistant messages with empty text, so they used to be
    invisible to the provider-facing recent message history. That made replies
    like "completemoslos" ambiguous even though the user was clearly referring
    to the last shared ficha/preference card. This is context, not a second
    intake brain: it exposes the objects that were actually rendered in chat.
    """

    objects: list[dict[str, Any]] = []
    for message in list(messages or ())[-12:]:
        profile_card = getattr(message, "profile_draft_card", None)
        if isinstance(profile_card, Mapping):
            objects.append(_profile_card_context(profile_card))
            continue
        preference_card = getattr(message, "preference_draft_card", None)
        if isinstance(preference_card, Mapping):
            objects.append(_generic_card_context("preference_draft_card", preference_card))
            continue
        proposal_card = getattr(message, "proposal_preferences_card", None)
        if isinstance(proposal_card, Mapping):
            objects.append(_generic_card_context("proposal_preferences_card", proposal_card))
            continue
        generated_card = getattr(message, "generated_plan_card", None)
        if isinstance(generated_card, Mapping):
            objects.append(_generic_card_context("generated_plan_card", generated_card))
    return objects[-6:]


def _profile_card_context(card: Mapping[str, Any]) -> dict[str, Any]:
    items = [item for item in card.get("items", []) or [] if isinstance(item, Mapping)]
    pending = [str(item.get("key") or "") for item in items if item.get("is_pending") and item.get("key")]
    known = [str(item.get("key") or "") for item in items if not item.get("is_pending") and item.get("key")]
    return {
        "type": "profile_draft_card",
        "title": _bounded_text(card.get("title") or "Ficha para esta propuesta"),
        "status": _bounded_text(card.get("status") or ""),
        "pending_count": int(card.get("pending_count") or len(pending)),
        "pending_fields": pending[:8],
        "known_fields": known[:8],
    }


def _generic_card_context(card_type: str, card: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "type": card_type,
        "title": _bounded_text(card.get("title") or card_type),
        "status": _bounded_text(card.get("status") or ""),
        "known_count": int(card.get("known_count") or 0),
    }


def _extract_nutrition_brief(conversation_state: Any | None) -> dict[str, Any]:
    result = getattr(conversation_state, "result", None)
    brief = getattr(result, "brief", None)
    if brief is None:
        return {}

    payload: dict[str, Any] = {}
    for field_name in NUTRITION_BRIEF_FIELDS:
        if field_name in PROVIDER_OMITTED_NUTRITION_BRIEF_FIELDS:
            continue
        value = getattr(brief, field_name, None)
        if _has_value(value):
            payload[field_name] = _sanitize_value(value)
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


def _bounded_text(value: Any, *, max_chars: int = MAX_TEXT_LENGTH) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}…"


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return bool(value)
    return True
