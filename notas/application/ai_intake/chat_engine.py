from __future__ import annotations

from dataclasses import replace

import json
import logging
import re
import unicodedata

from django.conf import settings

from ai_assistant.application.chat_engines import (
    ChatEngine,
    ChatEngineRequest,
    ChatEngineTurnResult,
)
from ai_assistant.application.context_builder import (
    build_safe_llm_context,
    merge_safe_context_into_request,
)
from ai_assistant.application.llm_chat_engine import ExternalLLMChatEngine
from ai_assistant.application.tools import (
    TOOL_READ_USER_PROFILE_CONTEXT,
    TOOL_SHARE_PREFERENCE_DRAFT_CARD,
    TOOL_SHARE_PROFILE_DRAFT_CARD,
    TOOL_SHARE_PROPOSAL_PREFERENCES_CARD,
)
from ai_assistant.application.rollout import AIRolloutDecision, resolve_ai_llm_rollout
from notas.application.ai_intake.deterministic_chat_engine import (
    DETERMINISTIC_ENGINE_MODE,
    DeterministicNutritionIntakeChatEngine,
)
from notas.application.ai_intake.nutrition_brief import (
    AI_NUTRITION_CONVERSATION_MESSAGE_LIMIT,
    NutritionBrief,
    PPK_WEIGHT_SOURCE_MANUAL,
    PPK_WEIGHT_SOURCE_PROFILE,
    NutritionConversationMessage,
    NutritionConversationState,
    build_llm_intake_result_from_brief,
    deserialize_conversation,
)

AI_ASSISTANT_CHAT_ENGINE_DETERMINISTIC = DETERMINISTIC_ENGINE_MODE
AI_ASSISTANT_CHAT_ENGINE_LLM_PREVIEW = "llm_preview"
AI_ASSISTANT_CHAT_ENGINE_LLM_PRODUCTION = "llm_production"
AI_ASSISTANT_CHAT_ENGINE_ALLOWED_MODES = (
    AI_ASSISTANT_CHAT_ENGINE_DETERMINISTIC,
    AI_ASSISTANT_CHAT_ENGINE_LLM_PREVIEW,
    AI_ASSISTANT_CHAT_ENGINE_LLM_PRODUCTION,
)
AI_ASSISTANT_PREVIEW_ACTION_TYPE = "assistant.ai_nutrition_intake.preview"
AI_ASSISTANT_PRODUCTION_ACTION_TYPE = "assistant.ai_nutrition_intake.production"

logger = logging.getLogger(__name__)


class LLMPreviewNutritionIntakeChatEngine:
    """LLM-led nutrition chat engine for the existing chat surface.

    In LLM modes the deterministic intake is not a co-author. The chat keeps
    `NutritionConversationState`/`NutritionBrief` as the typed persistence
    contract between turns, but the LLM leads the conversation and fills My
    Scoope objects through controlled tools. Deterministic intake remains
    available only as the explicit deterministic mode or an explicit rollout
    fallback. Provider failures return a technical message without invoking the
    deterministic interviewer.
    """

    engine_name = "llm_preview_nutrition_intake"

    def __init__(
        self,
        *,
        llm_engine: ChatEngine | None = None,
        baseline_engine: DeterministicNutritionIntakeChatEngine | None = None,
    ):
        self.llm_engine = llm_engine or ExternalLLMChatEngine()
        self.baseline_engine = baseline_engine

    def continue_chat(self, request: ChatEngineRequest) -> ChatEngineTurnResult:
        conversation_state = _llm_runtime_state_from_request(request)
        llm_text, llm_metadata = self._safe_llm_assistant_text(
            request,
            conversation_state=conversation_state,
        )
        conversation = _append_assistant_message(
            conversation_state,
            assistant_text=llm_text,
        )
        conversation, tool_state_patch_count = _apply_llm_tool_results_to_conversation_state(
            conversation,
            llm_metadata,
        )
        conversation, profile_card_count, preference_card_count, proposal_preferences_card_count = _append_draft_cards_from_llm_tools(
            conversation,
            llm_metadata,
        )
        return ChatEngineTurnResult(
            state=conversation,
            assistant_text=conversation.last_assistant_message,
            is_ready_for_proposal=conversation.is_ready_for_proposal,
            engine_name=self.engine_name,
            metadata={
                "surface": "ai_nutrition_intake",
                "mode": AI_ASSISTANT_CHAT_ENGINE_LLM_PREVIEW,
                "llm_runtime": "llm_led_tools_v1",
                "conversation_policy": "llm_tools",
                "deterministic_coauthor_disabled": True,
                "llm_tools_executed": bool(llm_metadata.get("tools_executed")),
                "llm_tool_requests": int(llm_metadata.get("tool_requests") or 0),
                "llm_semantic_intent": str(llm_metadata.get("semantic_intent") or ""),
                "llm_semantic_missing_slots": _safe_identifier_list(
                    llm_metadata.get("semantic_missing_slots")
                ),
                "llm_tool_results": _safe_tool_result_summaries(llm_metadata.get("tool_results")),
                "llm_tool_state_patches_applied": tool_state_patch_count,
                "llm_profile_draft_cards_rendered": profile_card_count,
                "llm_preference_draft_cards_rendered": preference_card_count,
                "llm_proposal_preferences_cards_rendered": proposal_preferences_card_count,
                "llm_preview_fallback": bool(llm_metadata.get("llm_preview_fallback")),
                "llm_preview_fallback_reason": llm_metadata.get("llm_preview_fallback_reason", ""),
                "llm_preview_fallback_kind": llm_metadata.get("llm_preview_fallback_kind", ""),
                "deterministic_runtime_invoked": bool(llm_metadata.get("deterministic_runtime_invoked")),
                "llm_visible_text_extracted": bool(llm_metadata.get("llm_visible_text_extracted")),
                "llm_provider": llm_metadata.get("provider", ""),
                "llm_model": llm_metadata.get("provider_model", ""),
                "usage_observability": dict(llm_metadata.get("usage_observability") or {}),
                "llm_provider_parse_error": str(llm_metadata.get("provider_parse_error") or ""),
                "llm_provider_contract_repair_attempted": bool(
                    llm_metadata.get("provider_contract_repair_attempted")
                ),
                "llm_provider_native_tool_transport": bool(
                    llm_metadata.get("provider_native_tool_transport")
                ),
                "llm_provider_native_tool_calls": int(
                    llm_metadata.get("provider_native_tool_calls") or 0
                ),
                "llm_provider_text_parse_ignored_due_to_native_tools": bool(
                    llm_metadata.get("provider_text_parse_ignored_due_to_native_tools")
                ),
                "llm_provider_incomplete_reasons": _safe_identifier_list(
                    llm_metadata.get("provider_incomplete_reasons")
                ),
                "llm_provider_final_incomplete_reason": str(
                    llm_metadata.get("provider_final_incomplete_reason") or ""
                ),
                "llm_tool_followup_local_ack": bool(
                    llm_metadata.get("tool_followup_local_ack")
                ),
                "llm_tool_followup_local_ack_policy": str(
                    llm_metadata.get("tool_followup_local_ack_policy") or ""
                ),
                "llm_provider_tool_followup_failed": bool(
                    llm_metadata.get("provider_tool_followup_failed")
                ),
                "context_builder": "safe_llm_context.v1",
            },
        )

    def _safe_llm_assistant_text(
        self,
        request: ChatEngineRequest,
        *,
        conversation_state: NutritionConversationState,
    ) -> tuple[str, dict]:
        try:
            turn_result = self._llm_turn_result(request, conversation_state=conversation_state)
        except Exception as exc:  # pragma: no cover - defensive preview boundary
            logger.warning("AI nutrition LLM preview provider failure: %s", exc)
            return (
                "No pude obtener una respuesta útil del proveedor externo en modo preview.",
                {
                    "llm_preview_fallback": True,
                    "llm_preview_error_type": exc.__class__.__name__,
                    "llm_preview_fallback_reason": "provider_failure",
                    "llm_preview_fallback_kind": "technical_message",
                    "deterministic_runtime_invoked": False,
                },
            )

        assistant_text = _visible_llm_assistant_text(turn_result.assistant_text)
        metadata = dict(turn_result.metadata or {})
        assistant_text = assistant_text or "No pude obtener una respuesta útil del proveedor externo en modo preview."
        if assistant_text != (turn_result.assistant_text or "").strip():
            metadata["llm_visible_text_extracted"] = True
        return assistant_text, metadata

    def _llm_turn_result(
        self,
        request: ChatEngineRequest,
        *,
        conversation_state: NutritionConversationState,
    ) -> ChatEngineTurnResult:
        safe_context = build_safe_llm_context(
            request,
            surface="ai_nutrition_intake",
            conversation_state=conversation_state,
            extra_context={"preview_mode": True, "llm_runtime": "llm_led_tools_v1"},
        )
        preview_request = merge_safe_context_into_request(request, safe_context=safe_context)
        preview_request = _with_preview_metadata(preview_request)
        return self.llm_engine.continue_chat(preview_request)



class LLMProductionNutritionIntakeChatEngine(LLMPreviewNutritionIntakeChatEngine):
    """Production LLM engine guarded by rollout policy.

    This mode is only reachable after explicit configuration and a positive
    rollout decision for the request. If the decision is negative, it returns
    the deterministic baseline for the same turn and annotates metadata so the
    UI/admin can see the fallback reason.
    """

    engine_name = "llm_production_nutrition_intake"

    def continue_chat(self, request: ChatEngineRequest) -> ChatEngineTurnResult:
        decision = resolve_ai_llm_rollout(request)
        if not decision.enabled:
            baseline_engine = self.baseline_engine or DeterministicNutritionIntakeChatEngine()
            baseline_result = baseline_engine.continue_chat(request)
            metadata = dict(baseline_result.metadata or {})
            metadata.update(
                {
                    "requested_mode": AI_ASSISTANT_CHAT_ENGINE_LLM_PRODUCTION,
                    "llm_production_enabled": False,
                    "llm_production_fallback": True,
                    "llm_production_fallback_kind": "explicit_deterministic_engine",
                    "deterministic_runtime_invoked": True,
                    "rollout": decision.as_metadata(),
                }
            )
            return ChatEngineTurnResult(
                state=baseline_result.state,
                assistant_text=baseline_result.assistant_text,
                is_ready_for_proposal=baseline_result.is_ready_for_proposal,
                engine_name=baseline_result.engine_name,
                metadata=metadata,
            )

        conversation_state = _llm_runtime_state_from_request(request)
        llm_text, llm_metadata = self._safe_llm_assistant_text(
            request,
            conversation_state=conversation_state,
            rollout_decision=decision,
        )
        conversation = _append_assistant_message(
            conversation_state,
            assistant_text=llm_text,
        )
        conversation, tool_state_patch_count = _apply_llm_tool_results_to_conversation_state(
            conversation,
            llm_metadata,
        )
        conversation, profile_card_count, preference_card_count, proposal_preferences_card_count = _append_draft_cards_from_llm_tools(
            conversation,
            llm_metadata,
        )
        return ChatEngineTurnResult(
            state=conversation,
            assistant_text=conversation.last_assistant_message,
            is_ready_for_proposal=conversation.is_ready_for_proposal,
            engine_name=self.engine_name,
            metadata={
                "surface": "ai_nutrition_intake",
                "mode": AI_ASSISTANT_CHAT_ENGINE_LLM_PRODUCTION,
                "llm_runtime": "llm_led_tools_v1",
                "conversation_policy": "llm_tools",
                "deterministic_coauthor_disabled": True,
                "llm_tools_executed": bool(llm_metadata.get("tools_executed")),
                "llm_tool_requests": int(llm_metadata.get("tool_requests") or 0),
                "llm_semantic_intent": str(llm_metadata.get("semantic_intent") or ""),
                "llm_semantic_missing_slots": _safe_identifier_list(
                    llm_metadata.get("semantic_missing_slots")
                ),
                "llm_tool_results": _safe_tool_result_summaries(llm_metadata.get("tool_results")),
                "llm_tool_state_patches_applied": tool_state_patch_count,
                "llm_profile_draft_cards_rendered": profile_card_count,
                "llm_preference_draft_cards_rendered": preference_card_count,
                "llm_proposal_preferences_cards_rendered": proposal_preferences_card_count,
                "llm_production_enabled": True,
                "llm_production_fallback": bool(llm_metadata.get("llm_production_fallback")),
                "llm_production_fallback_reason": llm_metadata.get("llm_production_fallback_reason", ""),
                "llm_production_fallback_kind": llm_metadata.get("llm_production_fallback_kind", ""),
                "deterministic_runtime_invoked": bool(llm_metadata.get("deterministic_runtime_invoked")),
                "llm_visible_text_extracted": bool(llm_metadata.get("llm_visible_text_extracted")),
                "llm_provider": llm_metadata.get("provider", ""),
                "llm_model": llm_metadata.get("provider_model", ""),
                "usage_observability": dict(llm_metadata.get("usage_observability") or {}),
                "llm_provider_parse_error": str(llm_metadata.get("provider_parse_error") or ""),
                "llm_provider_contract_repair_attempted": bool(
                    llm_metadata.get("provider_contract_repair_attempted")
                ),
                "llm_provider_native_tool_transport": bool(
                    llm_metadata.get("provider_native_tool_transport")
                ),
                "llm_provider_native_tool_calls": int(
                    llm_metadata.get("provider_native_tool_calls") or 0
                ),
                "llm_provider_text_parse_ignored_due_to_native_tools": bool(
                    llm_metadata.get("provider_text_parse_ignored_due_to_native_tools")
                ),
                "llm_provider_incomplete_reasons": _safe_identifier_list(
                    llm_metadata.get("provider_incomplete_reasons")
                ),
                "llm_provider_final_incomplete_reason": str(
                    llm_metadata.get("provider_final_incomplete_reason") or ""
                ),
                "llm_tool_followup_local_ack": bool(
                    llm_metadata.get("tool_followup_local_ack")
                ),
                "llm_tool_followup_local_ack_policy": str(
                    llm_metadata.get("tool_followup_local_ack_policy") or ""
                ),
                "llm_provider_tool_followup_failed": bool(
                    llm_metadata.get("provider_tool_followup_failed")
                ),
                "context_builder": "safe_llm_context.v1",
                "rollout": decision.as_metadata(),
            },
        )

    def _safe_llm_assistant_text(
        self,
        request: ChatEngineRequest,
        *,
        conversation_state: NutritionConversationState,
        rollout_decision: AIRolloutDecision | None = None,
    ) -> tuple[str, dict]:
        try:
            turn_result = self._llm_turn_result(
                request,
                conversation_state=conversation_state,
                rollout_decision=rollout_decision,
            )
        except Exception as exc:  # pragma: no cover - defensive production boundary
            logger.warning("AI nutrition LLM production provider failure: %s", exc)
            return (
                "No pude obtener una respuesta útil del proveedor externo en modo productivo.",
                {
                    "llm_production_fallback": True,
                    "llm_production_error_type": exc.__class__.__name__,
                    "llm_production_fallback_reason": "provider_failure",
                    "llm_production_fallback_kind": "technical_message",
                    "deterministic_runtime_invoked": False,
                },
            )

        assistant_text = _visible_llm_assistant_text(turn_result.assistant_text)
        metadata = dict(turn_result.metadata or {})
        assistant_text = assistant_text or "No pude obtener una respuesta útil del proveedor externo en modo productivo."
        if assistant_text != (turn_result.assistant_text or "").strip():
            metadata["llm_visible_text_extracted"] = True
        return assistant_text, metadata

    def _llm_turn_result(
        self,
        request: ChatEngineRequest,
        *,
        conversation_state: NutritionConversationState,
        rollout_decision: AIRolloutDecision | None = None,
    ) -> ChatEngineTurnResult:
        safe_context = build_safe_llm_context(
            request,
            surface="ai_nutrition_intake",
            conversation_state=conversation_state,
            extra_context={
                "preview_mode": False,
                "production_mode": True,
                "llm_runtime": "llm_led_tools_v1",
                "rollout_mode": (rollout_decision.mode if rollout_decision else "unknown"),
            },
        )
        production_request = merge_safe_context_into_request(request, safe_context=safe_context)
        production_request = _with_production_metadata(
            production_request,
            rollout_decision=rollout_decision,
        )
        return self.llm_engine.continue_chat(production_request)


def get_nutrition_intake_chat_engine_mode() -> str:
    """Return the configured safe chat engine mode for AI Nutrition Intake."""
    raw_mode = getattr(
        settings,
        "AI_ASSISTANT_CHAT_ENGINE_MODE",
        AI_ASSISTANT_CHAT_ENGINE_DETERMINISTIC,
    )
    mode = str(raw_mode or AI_ASSISTANT_CHAT_ENGINE_DETERMINISTIC).strip().lower()
    if mode not in AI_ASSISTANT_CHAT_ENGINE_ALLOWED_MODES:
        return AI_ASSISTANT_CHAT_ENGINE_DETERMINISTIC
    return mode


def get_nutrition_intake_chat_engine() -> ChatEngine:
    """Return the active engine for the existing nutrition chat surface.

    Default is deterministic. LLM preview requires explicit opt-in via
    `AI_ASSISTANT_CHAT_ENGINE_MODE=llm_preview`.
    """
    mode = get_nutrition_intake_chat_engine_mode()
    if mode == AI_ASSISTANT_CHAT_ENGINE_LLM_PREVIEW:
        return LLMPreviewNutritionIntakeChatEngine()
    if mode == AI_ASSISTANT_CHAT_ENGINE_LLM_PRODUCTION:
        return LLMProductionNutritionIntakeChatEngine()
    return DeterministicNutritionIntakeChatEngine()


def build_ai_nutrition_intake_engine_status() -> dict:
    """Return safe UI/debug metadata for the active AI Intake engine."""

    mode = get_nutrition_intake_chat_engine_mode()
    is_preview = mode == AI_ASSISTANT_CHAT_ENGINE_LLM_PREVIEW
    is_production = mode == AI_ASSISTANT_CHAT_ENGINE_LLM_PRODUCTION
    return {
        "mode": mode,
        "label": "LLM producción" if is_production else ("LLM preview" if is_preview else "Determinístico"),
        "is_llm_preview": is_preview,
        "is_llm_production": is_production,
        "rollout_enabled": bool(getattr(settings, "AI_ASSISTANT_LLM_ROLLOUT_ENABLED", False)),
        "rollout_mode": str(getattr(settings, "AI_ASSISTANT_LLM_ROLLOUT_MODE", "off") or "off"),
        "provider": str(getattr(settings, "AI_ASSISTANT_LLM_PROVIDER", "fake") or "fake"),
        "observability_enabled": bool(
            getattr(settings, "AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED", True)
        ),
        "guardrails_enabled": True,
        "proposal_tools_enabled": bool(
            getattr(settings, "AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS", False)
        ),
    }



def _llm_runtime_state_from_request(request: ChatEngineRequest) -> NutritionConversationState:
    """Build the typed chat state for an LLM-led turn without running intake logic.

    The state object remains the persistence contract for the chat surface,
    cards and proposal creation. It is not allowed to decide the next question
    in LLM modes; facts enter the brief through controlled tool results.
    """

    existing_state = deserialize_conversation(request.existing_payload)
    if existing_state is not None:
        messages = list(existing_state.messages)
        brief = existing_state.result.brief
    else:
        messages = []
        brief = NutritionBrief(raw_prompt=request.normalized_message)

    if request.normalized_message:
        messages.append(NutritionConversationMessage(role="user", text=request.normalized_message))

    return NutritionConversationState(
        messages=messages[-AI_NUTRITION_CONVERSATION_MESSAGE_LIMIT:],
        result=build_llm_intake_result_from_brief(brief),
    )


def _append_assistant_message(
    conversation: NutritionConversationState,
    *,
    assistant_text: str,
) -> NutritionConversationState:
    messages = list(conversation.messages)
    messages.append(
        NutritionConversationMessage(
            role="assistant",
            text=_visible_llm_assistant_text(str(assistant_text or "").strip()),
        )
    )
    return NutritionConversationState(
        messages=messages[-AI_NUTRITION_CONVERSATION_MESSAGE_LIMIT:],
        result=conversation.result,
    )

def _visible_llm_assistant_text(text: str) -> str:
    """Return only the human-readable assistant text for the nutrition chat UI.

    The external AI Assistant contract is structured JSON, but the `notas` chat
    surface persists a plain visible message in `NutritionConversationState`.
    This is the final UI boundary: even if a provider adapter, parser fallback or
    test stub returns the whole JSON envelope as text, the chat bubble only gets
    `assistant_message.content`.
    """

    cleaned = str(text or "").strip()
    if not cleaned:
        return ""

    payload = _loads_llm_json_payload(cleaned) or _find_embedded_llm_json_payload(cleaned)
    if payload is None:
        jsonish_content = _extract_jsonish_assistant_content(cleaned)
        return jsonish_content or cleaned

    content = _assistant_content_from_payload(payload)
    if content:
        return content

    jsonish_content = _extract_jsonish_assistant_content(cleaned)
    return jsonish_content or cleaned


def _assistant_content_from_payload(payload: dict) -> str:
    assistant_message = payload.get("assistant_message")
    if isinstance(assistant_message, dict):
        content = assistant_message.get("content") or assistant_message.get("text") or ""
    else:
        content = assistant_message or payload.get("assistant_text") or payload.get("message") or ""
    return str(content or "").strip()


def _loads_llm_json_payload(text: str) -> dict | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(
            line for line in cleaned.splitlines() if not line.strip().startswith("```")
        ).strip()
    if not (cleaned.startswith("{") and cleaned.endswith("}")):
        return None
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _find_embedded_llm_json_payload(text: str) -> dict | None:
    """Find a structured assistant envelope embedded inside surrounding text."""

    if "assistant_message" not in text:
        return None

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and "assistant_message" in payload:
            return payload
    return None


def _extract_jsonish_assistant_content(text: str) -> str:
    """Best-effort extraction for almost-JSON envelopes returned as visible text."""

    if "assistant_message" not in text:
        return ""

    pattern = re.compile(
        r'"assistant_message"\s*:\s*\{.*?"(?:content|text)"\s*:\s*"(?P<content>(?:\\.|[^"\\])*)"',
        flags=re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return ""

    raw = match.group("content")
    try:
        return json.loads(f'"{raw}"').strip()
    except json.JSONDecodeError:
        return raw.replace("\\n", "\n").replace("\\\"", '"').strip()


def _with_preview_metadata(request: ChatEngineRequest) -> ChatEngineRequest:
    return _with_llm_mode_metadata(
        request,
        action_type=AI_ASSISTANT_PREVIEW_ACTION_TYPE,
        chat_engine_mode=AI_ASSISTANT_CHAT_ENGINE_LLM_PREVIEW,
    )


def _with_production_metadata(
    request: ChatEngineRequest,
    *,
    rollout_decision: AIRolloutDecision | None = None,
) -> ChatEngineRequest:
    metadata = dict(request.metadata or {})
    if rollout_decision is not None:
        metadata["rollout"] = rollout_decision.as_metadata()
    return _with_llm_mode_metadata(
        ChatEngineRequest(
            message=request.message,
            existing_payload=request.existing_payload,
            user_id=request.user_id,
            metadata=metadata,
        ),
        action_type=AI_ASSISTANT_PRODUCTION_ACTION_TYPE,
        chat_engine_mode=AI_ASSISTANT_CHAT_ENGINE_LLM_PRODUCTION,
    )


def _with_llm_mode_metadata(
    request: ChatEngineRequest,
    *,
    action_type: str,
    chat_engine_mode: str,
) -> ChatEngineRequest:
    metadata = dict(request.metadata or {})
    metadata.setdefault("action_type", action_type)
    metadata.setdefault("ai_action_type", action_type)
    metadata.setdefault("surface", "ai_nutrition_intake")
    metadata.setdefault("chat_engine_mode", chat_engine_mode)
    return ChatEngineRequest(
        message=request.message,
        existing_payload=request.existing_payload,
        user_id=request.user_id,
        metadata=metadata,
    )


def _safe_identifier_list(value: object, *, limit: int = 24) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    identifiers: list[str] = []
    for item in value:
        identifier = str(item or "").strip().lower()
        if not identifier or identifier in identifiers:
            continue
        identifiers.append(identifier[:80])
        if len(identifiers) >= limit:
            break
    return identifiers


def _safe_tool_result_summaries(value: object, *, limit: int = 12) -> list[dict[str, str]]:
    if not isinstance(value, (list, tuple)):
        return []
    summaries: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        tool_name = str(item.get("tool_name") or "").strip().lower()
        status = str(item.get("status") or "").strip().lower()
        if not tool_name:
            continue
        summary = {
            "tool_name": tool_name[:120],
            "status": status[:40],
        }
        error_code = str(item.get("error_code") or "").strip().lower()
        if error_code:
            summary["error_code"] = error_code[:120]
        summaries.append(summary)
        if len(summaries) >= limit:
            break
    return summaries


def _apply_llm_tool_results_to_conversation_state(
    conversation: NutritionConversationState,
    metadata: dict,
) -> tuple[NutritionConversationState, int]:
    """Fold successful tool outputs into the conversation-scoped typed state.

    The synchronized result uses the LLM state-only builder: it updates cards,
    provenance and proposal readiness without calculating a backend-owned next
    question or pending conversational slot.
    """

    tool_results = list((metadata or {}).get("tool_results") or [])
    if not tool_results:
        return conversation, 0

    brief = conversation.result.brief
    updated_brief = brief
    applied_count = 0

    for tool_result in tool_results:
        if not isinstance(tool_result, dict) or tool_result.get("status") != "ok":
            continue
        data = tool_result.get("data") or {}
        if not isinstance(data, dict):
            continue

        patched_brief = _apply_llm_tool_result_data_to_brief(updated_brief, data)
        if patched_brief != updated_brief:
            updated_brief = patched_brief
            applied_count += 1

    if not applied_count:
        return conversation, 0

    return (
        NutritionConversationState(
            messages=list(conversation.messages)[-AI_NUTRITION_CONVERSATION_MESSAGE_LIMIT:],
            result=build_llm_intake_result_from_brief(updated_brief),
        ),
        applied_count,
    )


def _apply_llm_tool_result_data_to_brief(brief: NutritionBrief, data: dict) -> NutritionBrief:
    updated = brief
    profile_draft = data.get("profile_draft")
    if isinstance(profile_draft, dict):
        updated = _apply_profile_draft_to_brief(updated, profile_draft)

    preference_draft = data.get("preference_draft")
    if isinstance(preference_draft, dict):
        updated = _apply_preference_draft_to_brief(updated, preference_draft)

    proposal_preferences = data.get("proposal_preferences")
    if isinstance(proposal_preferences, dict):
        updated = _apply_proposal_preferences_to_brief(updated, proposal_preferences)

    nutrition_brief_patch = data.get("nutrition_brief_patch")
    if isinstance(nutrition_brief_patch, dict):
        patch = dict(nutrition_brief_patch)
        if isinstance(proposal_preferences, dict):
            # Proposal draft fields were already synchronized with their own
            # provenance. The companion patch is intentionally redundant for
            # older consumers and must not overwrite those source labels.
            patch = {
                field_name: value
                for field_name, value in patch.items()
                if field_name not in proposal_preferences
            }
        updated = _apply_nutrition_brief_patch(updated, patch, default_source="chat_draft")

    return updated


def _apply_profile_draft_to_brief(brief: NutritionBrief, profile_draft: dict) -> NutritionBrief:
    allowed_fields = {
        "weight_kg",
        "height_cm",
        "age_years",
        "sex",
        "activity_level",
        "training_frequency",
    }
    updates: dict[str, object] = {}
    source_updates: dict[str, str] = {}
    field_sources = profile_draft.get("field_sources") if isinstance(profile_draft.get("field_sources"), dict) else {}

    for field_name in allowed_fields:
        if field_name not in profile_draft:
            continue
        value = profile_draft.get(field_name)
        if _tool_value_is_empty(value):
            continue
        updates[field_name] = value
        source_updates[field_name] = _normalize_tool_source(field_sources.get(field_name), default="chat_draft")

    # Weight source is internal calculation metadata, not a user-facing question.
    # If a user provides weight through the chat draft, treat it as current for
    # this proposal. If it came from the persisted ficha and no source is known,
    # keep the profile source for estimator/audit purposes.
    if "weight_kg" in updates:
        weight_source = source_updates.get("weight_kg")
        if weight_source in {"chat_draft", "manual"}:
            updates["ppk_weight_source"] = PPK_WEIGHT_SOURCE_MANUAL
        elif weight_source == "profile" and not brief.ppk_weight_source:
            updates["ppk_weight_source"] = PPK_WEIGHT_SOURCE_PROFILE

    return _replace_brief_fields(brief, updates, source_updates=source_updates)


def _apply_preference_draft_to_brief(brief: NutritionBrief, preference_draft: dict) -> NutritionBrief:
    updates: dict[str, object] = {}
    source_updates: dict[str, str] = {}
    field_sources = (
        preference_draft.get("field_sources")
        if isinstance(preference_draft.get("field_sources"), dict)
        else {}
    )

    avoided_foods = preference_draft.get("avoided_foods")
    if not _tool_value_is_empty(avoided_foods):
        updates["excluded_foods"] = _merge_text_lists(brief.excluded_foods, avoided_foods)
        source_updates["excluded_foods"] = _normalize_tool_source(
            field_sources.get("avoided_foods"),
            default="chat_draft",
        )

    preferred_foods = preference_draft.get("preferred_foods")
    if not _tool_value_is_empty(preferred_foods):
        updates["preferred_foods"] = _merge_text_lists(brief.preferred_foods, preferred_foods)
        source_updates["preferred_foods"] = _normalize_tool_source(
            field_sources.get("preferred_foods"),
            default="chat_draft",
        )

    preferred_meals = preference_draft.get("preferred_meals_per_day")
    if not _tool_value_is_empty(preferred_meals) and not brief.meals_per_day:
        updates["meals_per_day"] = preferred_meals
        source_updates["meals_per_day"] = _normalize_tool_source(
            field_sources.get("preferred_meals_per_day"),
            default="chat_draft",
        )

    budget = preference_draft.get("budget_preference")
    if not _tool_value_is_empty(budget) and not brief.budget_level:
        updates["budget_level"] = budget
        source_updates["budget_level"] = _normalize_tool_source(
            field_sources.get("budget_preference"),
            default="chat_draft",
        )

    simplicity = preference_draft.get("simplicity_preference")
    if not _tool_value_is_empty(simplicity):
        if str(simplicity) in {"high", "medium"}:
            updates["style_preferences"] = _merge_text_lists(brief.style_preferences, ["simple"])
            source_updates["style_preferences"] = _normalize_tool_source(
                field_sources.get("simplicity_preference"),
                default="chat_draft",
            )
        if str(simplicity) == "high" and not brief.complexity_level:
            updates["complexity_level"] = "low"
            source_updates["complexity_level"] = _normalize_tool_source(
                field_sources.get("simplicity_preference"),
                default="chat_draft",
            )

    variety = preference_draft.get("variety_preference")
    if not _tool_value_is_empty(variety):
        if str(variety) in {"high", "medium"}:
            base_styles = updates.get("style_preferences", brief.style_preferences)
            updates["style_preferences"] = _merge_text_lists(base_styles, ["varied"])
            source_updates["style_preferences"] = _normalize_tool_source(
                field_sources.get("variety_preference"),
                default="chat_draft",
            )
        if str(variety) == "high" and not brief.complexity_level:
            updates["complexity_level"] = "high"
            source_updates["complexity_level"] = _normalize_tool_source(
                field_sources.get("variety_preference"),
                default="chat_draft",
            )

    dietary_pattern = preference_draft.get("dietary_pattern")
    allergies = preference_draft.get("allergies_or_intolerances")
    notes = list(brief.notes)
    if not _tool_value_is_empty(dietary_pattern):
        notes = _merge_text_lists(notes, [f"Patrón alimentario declarado: {dietary_pattern}."])
    if not _tool_value_is_empty(allergies):
        notes = _merge_text_lists(notes, [f"Alergias o intolerancias declaradas: {', '.join(_coerce_text_list(allergies))}."])
    if notes != brief.notes:
        updates["notes"] = notes
        note_sources = [
            field_sources.get("dietary_pattern") if not _tool_value_is_empty(dietary_pattern) else None,
            field_sources.get("allergies_or_intolerances") if not _tool_value_is_empty(allergies) else None,
        ]
        source_updates["notes"] = next(
            (
                _normalize_tool_source(source, default="chat_draft")
                for source in note_sources
                if source
            ),
            "chat_draft",
        )

    return _replace_brief_fields(brief, updates, source_updates=source_updates)


def _apply_proposal_preferences_to_brief(brief: NutritionBrief, proposal_preferences: dict) -> NutritionBrief:
    updates = {
        field_name: proposal_preferences.get(field_name)
        for field_name in (
            "goal",
            "requested_entity",
            "meals_per_day",
            "energy_adjustment",
            "complexity_level",
            "calorie_target",
            "protein_target",
            "carb_target",
            "fat_target",
            "notes",
        )
        if field_name in proposal_preferences and not _tool_value_is_empty(proposal_preferences.get(field_name))
    }
    field_sources = (
        proposal_preferences.get("field_sources")
        if isinstance(proposal_preferences.get("field_sources"), dict)
        else {}
    )
    source_updates = {
        field_name: _normalize_tool_source(field_sources.get(field_name), default="chat_draft")
        for field_name in updates
    }
    return _replace_brief_fields(brief, updates, source_updates=source_updates)


def _apply_nutrition_brief_patch(
    brief: NutritionBrief,
    patch: dict,
    *,
    default_source: str,
) -> NutritionBrief:
    allowed_fields = {
        "subject_source",
        "ppk_weight_source",
        "goal",
        "requested_entity",
        "meals_per_day",
        "energy_adjustment",
        "calorie_target",
        "protein_target",
        "carb_target",
        "fat_target",
        "notes",
    }
    updates = {
        field_name: value
        for field_name, value in patch.items()
        if field_name in allowed_fields and not _tool_value_is_empty(value)
    }
    return _replace_brief_fields(
        brief,
        updates,
        source_updates={field_name: default_source for field_name in updates},
    )


def _replace_brief_fields(
    brief: NutritionBrief,
    updates: dict[str, object],
    *,
    source_updates: dict[str, str] | None = None,
) -> NutritionBrief:
    if not updates:
        return brief

    normalized_updates: dict[str, object] = {}
    for field_name, value in updates.items():
        if not hasattr(brief, field_name):
            continue
        if field_name in {"notes", "style_preferences", "excluded_foods", "preferred_foods"}:
            value = _coerce_text_list(value)
        normalized_updates[field_name] = value

    if not normalized_updates:
        return brief

    field_sources = dict(brief.field_sources or {})
    for field_name, source in dict(source_updates or {}).items():
        if field_name in normalized_updates:
            field_sources[field_name] = _normalize_tool_source(source, default="chat_draft")
    if field_sources != (brief.field_sources or {}):
        normalized_updates["field_sources"] = field_sources

    return replace(brief, **normalized_updates)


def _normalize_tool_source(value: object, *, default: str) -> str:
    source = str(value or "").strip().lower()
    return source if source in {"profile", "chat_draft", "manual", "unknown"} else default


def _tool_value_is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _merge_text_lists(existing: object, incoming: object) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in [*_coerce_text_list(existing), *_coerce_text_list(incoming)]:
        key = _normalize_text_key(item)
        if not key or key in seen:
            continue
        seen.add(key)
        values.append(str(item).strip())
    return values


def _normalize_text_key(value: object) -> str:
    """Normalize a value for state-level list de-duplication only."""

    text = " ".join(str(value or "").casefold().split())
    text = "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"[^a-z0-9ñ\s]", "", text)


def _coerce_text_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = value.replace(";", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        parts = list(value)
    else:
        parts = [value]
    return [" ".join(str(item or "").strip().split()) for item in parts if str(item or "").strip()]


def _append_draft_cards_from_llm_tools(
    conversation: NutritionConversationState,
    metadata: dict,
) -> tuple[NutritionConversationState, int, int, int]:
    """Append chat-renderable profile cards produced by controlled LLM tools.

    Draft updates and UI presentation are separate capabilities. Update tools
    synchronize conversation state silently; only explicit card-producing tools
    may append product objects to the chat thread. This prevents a new card from
    appearing after every individual fact while preserving initial profile cards
    and deliberate review moments.
    """

    profile_cards = _profile_draft_cards_from_llm_metadata(metadata)
    preference_cards = _preference_draft_cards_from_llm_metadata(metadata)
    proposal_preferences_cards = _proposal_preferences_cards_from_llm_metadata(metadata)
    if not profile_cards and not preference_cards and not proposal_preferences_cards:
        return conversation, 0, 0, 0

    messages = list(conversation.messages)
    seen_profile_signatures = {
        _profile_draft_card_signature(message.profile_draft_card)
        for message in messages
        if getattr(message, "profile_draft_card", None)
    }
    seen_preference_signatures = {
        _preference_draft_card_signature(message.preference_draft_card)
        for message in messages
        if getattr(message, "preference_draft_card", None)
    }
    seen_proposal_preferences_signatures = {
        _proposal_preferences_card_signature(message.proposal_preferences_card)
        for message in messages
        if getattr(message, "proposal_preferences_card", None)
    }
    profile_appended = 0
    preference_appended = 0
    proposal_preferences_appended = 0
    for card in profile_cards:
        signature = _profile_draft_card_signature(card)
        if not signature or signature in seen_profile_signatures:
            continue
        messages.append(
            NutritionConversationMessage(
                role="assistant",
                text="",
                profile_draft_card=card,
            )
        )
        seen_profile_signatures.add(signature)
        profile_appended += 1
    for card in preference_cards:
        signature = _preference_draft_card_signature(card)
        if not signature or signature in seen_preference_signatures:
            continue
        messages.append(
            NutritionConversationMessage(
                role="assistant",
                text="",
                preference_draft_card=card,
            )
        )
        seen_preference_signatures.add(signature)
        preference_appended += 1

    for card in proposal_preferences_cards:
        signature = _proposal_preferences_card_signature(card)
        if not signature or signature in seen_proposal_preferences_signatures:
            continue
        messages.append(
            NutritionConversationMessage(
                role="assistant",
                text="",
                proposal_preferences_card=card,
            )
        )
        seen_proposal_preferences_signatures.add(signature)
        proposal_preferences_appended += 1

    if not (profile_appended or preference_appended or proposal_preferences_appended):
        return conversation, 0, 0, 0
    return (
        NutritionConversationState(
            messages=messages[-AI_NUTRITION_CONVERSATION_MESSAGE_LIMIT:],
            result=conversation.result,
        ),
        profile_appended,
        preference_appended,
        proposal_preferences_appended,
    )



def _append_profile_draft_cards_from_llm_tools(
    conversation: NutritionConversationState,
    metadata: dict,
) -> tuple[NutritionConversationState, int]:
    """Backward-compatible helper for profile-card-only tests/callers.

    CM06/CM07 generalized the card append path to include preference and
    proposal-preference cards. Some focused tests still exercise the profile
    card boundary directly, so keep this thin wrapper around the unified helper.
    """

    updated, profile_count, _preference_count, _proposal_preferences_count = _append_draft_cards_from_llm_tools(
        conversation,
        metadata,
    )
    return updated, profile_count


def _profile_draft_cards_from_llm_metadata(metadata: dict) -> list[dict]:
    cards: list[dict] = []
    for tool_result in list((metadata or {}).get("tool_results") or []):
        if not isinstance(tool_result, dict):
            continue
        if tool_result.get("status") != "ok":
            continue
        if tool_result.get("tool_name") not in {
            TOOL_READ_USER_PROFILE_CONTEXT,
            TOOL_SHARE_PROFILE_DRAFT_CARD,
        }:
            continue
        data = tool_result.get("data") or {}
        if not isinstance(data, dict):
            continue
        card = data.get("profile_draft_card")
        normalized_card = _normalize_profile_draft_card_payload(card)
        if normalized_card:
            cards.append(normalized_card)
    return cards


def _normalize_profile_draft_card_payload(card: object) -> dict | None:
    if not isinstance(card, dict):
        return None
    items = []
    for raw_item in list(card.get("items") or []):
        if not isinstance(raw_item, dict):
            continue
        items.append(
            {
                "key": str(raw_item.get("key") or "").strip(),
                "label": str(raw_item.get("label") or "").strip(),
                "value": str(raw_item.get("value") or "").strip(),
                "is_pending": bool(raw_item.get("is_pending")),
                "source": str(raw_item.get("source") or "unknown").strip(),
                "source_label": str(raw_item.get("source_label") or "Pendiente").strip(),
            }
        )
    if not items:
        return None
    try:
        pending_count = int(card.get("pending_count") or 0)
    except (TypeError, ValueError):
        pending_count = sum(1 for item in items if item["is_pending"])
    status = str(card.get("status") or ("complete" if pending_count == 0 else "pending")).strip()
    committable_keys = {"weight_kg", "height_cm", "sex"}
    has_committable_profile_updates = any(
        item["key"] in committable_keys
        and item["source"] == "chat_draft"
        and not item["is_pending"]
        for item in items
    )
    can_update = (
        pending_count == 0
        and has_committable_profile_updates
        and bool(card.get("can_update_personal_profile", True))
    )
    return {
        "title": str(card.get("title") or "Ficha para esta propuesta").strip(),
        "subtitle": str(card.get("subtitle") or "Datos personales usados en esta conversación.").strip(),
        "items": items,
        "pending_count": pending_count,
        "has_chat_draft_updates": bool(card.get("has_chat_draft_updates")),
        "has_committable_profile_updates": has_committable_profile_updates,
        "can_update_personal_profile": can_update,
        "status": status,
    }


def _profile_draft_card_signature(card: object) -> tuple | None:
    if not isinstance(card, dict):
        return None
    items = tuple(
        (
            str(item.get("key") or ""),
            str(item.get("value") or ""),
            str(item.get("source") or ""),
            bool(item.get("is_pending")),
        )
        for item in list(card.get("items") or [])
        if isinstance(item, dict)
    )
    if not items:
        return None
    return (
        str(card.get("title") or ""),
        str(card.get("status") or ""),
        int(card.get("pending_count") or 0),
        items,
    )

def _preference_draft_cards_from_llm_metadata(metadata: dict) -> list[dict]:
    cards: list[dict] = []
    for tool_result in list((metadata or {}).get("tool_results") or []):
        if not isinstance(tool_result, dict):
            continue
        if tool_result.get("status") != "ok":
            continue
        if tool_result.get("tool_name") != TOOL_SHARE_PREFERENCE_DRAFT_CARD:
            continue
        data = tool_result.get("data") or {}
        if not isinstance(data, dict):
            continue
        card = data.get("preference_draft_card")
        normalized_card = _normalize_preference_draft_card_payload(card)
        if normalized_card:
            cards.append(normalized_card)
    return cards


def _normalize_preference_draft_card_payload(card: object) -> dict | None:
    if not isinstance(card, dict):
        return None
    sections = []
    for raw_section in list(card.get("sections") or []):
        if not isinstance(raw_section, dict):
            continue
        items = []
        for raw_item in list(raw_section.get("items") or []):
            if not isinstance(raw_item, dict):
                continue
            items.append(
                {
                    "key": str(raw_item.get("key") or "").strip(),
                    "label": str(raw_item.get("label") or "").strip(),
                    "value": str(raw_item.get("value") or "").strip(),
                    "is_pending": bool(raw_item.get("is_pending")),
                    "source": str(raw_item.get("source") or "unknown").strip(),
                    "source_label": str(raw_item.get("source_label") or "Pendiente").strip(),
                }
            )
        if items:
            sections.append(
                {
                    "title": str(raw_section.get("title") or "Preferencias").strip(),
                    "items": items,
                }
            )
    if not sections:
        return None
    try:
        known_count = int(card.get("known_count") or 0)
    except (TypeError, ValueError):
        known_count = sum(
            1
            for section in sections
            for item in section["items"]
            if not item["is_pending"]
        )
    status = str(card.get("status") or ("has_data" if known_count else "empty")).strip()
    return {
        "title": str(card.get("title") or "Preferencias para esta propuesta").strip(),
        "subtitle": str(card.get("subtitle") or "Información usada en esta conversación.").strip(),
        "sections": sections,
        "known_count": known_count,
        "has_chat_draft_updates": bool(card.get("has_chat_draft_updates")),
        "can_update_preferences": bool(card.get("can_update_preferences")),
        "status": status,
    }


def _preference_draft_card_signature(card: object) -> tuple | None:
    if not isinstance(card, dict):
        return None
    items = tuple(
        (
            str(section.get("title") or ""),
            tuple(
                (
                    str(item.get("key") or ""),
                    str(item.get("value") or ""),
                    str(item.get("source") or ""),
                    bool(item.get("is_pending")),
                )
                for item in list(section.get("items") or [])
                if isinstance(item, dict)
            ),
        )
        for section in list(card.get("sections") or [])
        if isinstance(section, dict)
    )
    if not items:
        return None
    return (
        str(card.get("title") or ""),
        str(card.get("status") or ""),
        int(card.get("known_count") or 0),
        items,
    )


def _proposal_preferences_cards_from_llm_metadata(metadata: dict) -> list[dict]:
    cards: list[dict] = []
    for tool_result in list((metadata or {}).get("tool_results") or []):
        if not isinstance(tool_result, dict):
            continue
        if tool_result.get("status") != "ok":
            continue
        if tool_result.get("tool_name") != TOOL_SHARE_PROPOSAL_PREFERENCES_CARD:
            continue
        data = tool_result.get("data") or {}
        if not isinstance(data, dict):
            continue
        card = data.get("proposal_preferences_card")
        normalized_card = _normalize_proposal_preferences_card_payload(card)
        if normalized_card:
            cards.append(normalized_card)
    return cards


def _normalize_proposal_preferences_card_payload(card: object) -> dict | None:
    if not isinstance(card, dict):
        return None
    sections = []
    for raw_section in list(card.get("sections") or []):
        if not isinstance(raw_section, dict):
            continue
        items = []
        for raw_item in list(raw_section.get("items") or []):
            if not isinstance(raw_item, dict):
                continue
            items.append(
                {
                    "key": str(raw_item.get("key") or "").strip(),
                    "label": str(raw_item.get("label") or "").strip(),
                    "value": str(raw_item.get("value") or "").strip(),
                    "is_pending": bool(raw_item.get("is_pending")),
                    "source": str(raw_item.get("source") or "unknown").strip(),
                    "source_label": str(raw_item.get("source_label") or "Pendiente").strip(),
                }
            )
        if items:
            sections.append(
                {
                    "title": str(raw_section.get("title") or "Preferencias de propuesta").strip(),
                    "items": items,
                }
            )
    if not sections:
        return None
    try:
        known_count = int(card.get("known_count") or 0)
    except (TypeError, ValueError):
        known_count = sum(
            1
            for section in sections
            for item in section["items"]
            if not item["is_pending"]
        )
    status = str(card.get("status") or ("has_data" if known_count else "empty")).strip()
    return {
        "title": str(card.get("title") or "Preferencias de propuesta").strip(),
        "subtitle": str(card.get("subtitle") or "Parámetros usados solo para esta propuesta.").strip(),
        "sections": sections,
        "known_count": known_count,
        "has_chat_draft_updates": bool(card.get("has_chat_draft_updates")),
        "can_create_proposal": bool(card.get("can_create_proposal")),
        "proposal_scoped_only": bool(card.get("proposal_scoped_only")),
        "status": status,
    }


def _proposal_preferences_card_signature(card: object) -> tuple | None:
    if not isinstance(card, dict):
        return None
    items = tuple(
        (
            str(section.get("title") or ""),
            tuple(
                (
                    str(item.get("key") or ""),
                    str(item.get("value") or ""),
                    str(item.get("source") or ""),
                    bool(item.get("is_pending")),
                )
                for item in list(section.get("items") or [])
                if isinstance(item, dict)
            ),
        )
        for section in list(card.get("sections") or [])
        if isinstance(section, dict)
    )
    if not items:
        return None
    return (
        str(card.get("title") or ""),
        str(card.get("status") or ""),
        int(card.get("known_count") or 0),
        items,
    )
