from __future__ import annotations

from dataclasses import replace

import logging

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
from ai_assistant.application.rollout import AIRolloutDecision, resolve_ai_llm_rollout
from notas.application.ai_intake.nutrition_brief import (
    NutritionConversationMessage,
    NutritionConversationState,
    start_or_continue_conversation,
)

AI_ASSISTANT_CHAT_ENGINE_DETERMINISTIC = "deterministic"
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


class DeterministicNutritionIntakeChatEngine:
    """Adapter from the current AI Intake flow to the AI Assistant engine contract.

    Patch 42 keeps the existing deterministic/semi-deterministic intake logic as
    the safe baseline. Patch 51 keeps this engine as the default and introduces
    explicit selection for LLM preview mode.
    """

    engine_name = "deterministic_nutrition_intake"

    def continue_chat(self, request: ChatEngineRequest) -> ChatEngineTurnResult:
        conversation = start_or_continue_conversation(
            message=request.normalized_message,
            existing_payload=request.existing_payload,
            user=(request.metadata or {}).get("tool_user"),
        )
        return ChatEngineTurnResult(
            state=conversation,
            assistant_text=conversation.last_assistant_message,
            is_ready_for_proposal=conversation.is_ready_for_proposal,
            engine_name=self.engine_name,
            metadata={
                "surface": "ai_nutrition_intake",
                "mode": AI_ASSISTANT_CHAT_ENGINE_DETERMINISTIC,
            },
        )


class LLMPreviewNutritionIntakeChatEngine:
    """Preview engine for the existing nutrition chat surface.

    The preview mode lets the external LLM produce the visible assistant text,
    but the persisted conversation state remains a `NutritionConversationState`
    built by My Scoope's deterministic intake flow. This keeps the current UI,
    session serialization and proposal creation flow stable while the LLM is
    still not allowed to execute tools or create proposals.
    """

    engine_name = "llm_preview_nutrition_intake"

    def __init__(
        self,
        *,
        llm_engine: ChatEngine | None = None,
        baseline_engine: DeterministicNutritionIntakeChatEngine | None = None,
    ):
        self.llm_engine = llm_engine or ExternalLLMChatEngine()
        self.baseline_engine = baseline_engine or DeterministicNutritionIntakeChatEngine()

    def continue_chat(self, request: ChatEngineRequest) -> ChatEngineTurnResult:
        baseline_result = self.baseline_engine.continue_chat(request)
        llm_text, llm_metadata = self._safe_llm_assistant_text(
            request,
            baseline_state=baseline_result.state,
        )
        conversation = _replace_last_assistant_message(
            baseline_result.state,
            assistant_text=llm_text,
        )
        return ChatEngineTurnResult(
            state=conversation,
            assistant_text=conversation.last_assistant_message,
            is_ready_for_proposal=conversation.is_ready_for_proposal,
            engine_name=self.engine_name,
            metadata={
                "surface": "ai_nutrition_intake",
                "mode": AI_ASSISTANT_CHAT_ENGINE_LLM_PREVIEW,
                "baseline_engine": baseline_result.engine_name,
                "llm_tools_executed": bool(llm_metadata.get("tools_executed")),
                "llm_tool_requests": int(llm_metadata.get("tool_requests") or 0),
                "llm_preview_fallback": bool(llm_metadata.get("llm_preview_fallback")),
                "llm_provider": llm_metadata.get("provider", ""),
                "llm_model": llm_metadata.get("provider_model", ""),
                "usage_observability": dict(llm_metadata.get("usage_observability") or {}),
                "context_builder": "safe_llm_context.v1",
            },
        )

    def _safe_llm_assistant_text(
        self,
        request: ChatEngineRequest,
        *,
        baseline_state: NutritionConversationState,
    ) -> tuple[str, dict]:
        try:
            turn_result = self._llm_turn_result(request, baseline_state=baseline_state)
        except Exception as exc:  # pragma: no cover - defensive preview boundary
            logger.warning("AI nutrition LLM preview fallback: %s", exc)
            return (
                baseline_state.last_assistant_message
                or "No pude obtener una respuesta útil del proveedor externo en modo preview.",
                {
                    "llm_preview_fallback": True,
                    "llm_preview_error_type": exc.__class__.__name__,
                },
            )

        assistant_text = turn_result.assistant_text.strip() or (
            baseline_state.last_assistant_message
            or "No pude obtener una respuesta útil del proveedor externo en modo preview."
        )
        return assistant_text, dict(turn_result.metadata or {})

    def _llm_turn_result(
        self,
        request: ChatEngineRequest,
        *,
        baseline_state: NutritionConversationState,
    ) -> ChatEngineTurnResult:
        safe_context = build_safe_llm_context(
            request,
            surface="ai_nutrition_intake",
            conversation_state=baseline_state,
            extra_context={"preview_mode": True},
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
            baseline_result = self.baseline_engine.continue_chat(request)
            metadata = dict(baseline_result.metadata or {})
            metadata.update(
                {
                    "requested_mode": AI_ASSISTANT_CHAT_ENGINE_LLM_PRODUCTION,
                    "llm_production_enabled": False,
                    "llm_production_fallback": True,
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

        baseline_result = self.baseline_engine.continue_chat(request)
        llm_text, llm_metadata = self._safe_llm_assistant_text(
            request,
            baseline_state=baseline_result.state,
            rollout_decision=decision,
        )
        conversation = _replace_last_assistant_message(
            baseline_result.state,
            assistant_text=llm_text,
        )
        return ChatEngineTurnResult(
            state=conversation,
            assistant_text=conversation.last_assistant_message,
            is_ready_for_proposal=conversation.is_ready_for_proposal,
            engine_name=self.engine_name,
            metadata={
                "surface": "ai_nutrition_intake",
                "mode": AI_ASSISTANT_CHAT_ENGINE_LLM_PRODUCTION,
                "baseline_engine": baseline_result.engine_name,
                "llm_tools_executed": bool(llm_metadata.get("tools_executed")),
                "llm_tool_requests": int(llm_metadata.get("tool_requests") or 0),
                "llm_production_enabled": True,
                "llm_production_fallback": bool(llm_metadata.get("llm_production_fallback")),
                "llm_provider": llm_metadata.get("provider", ""),
                "llm_model": llm_metadata.get("provider_model", ""),
                "usage_observability": dict(llm_metadata.get("usage_observability") or {}),
                "context_builder": "safe_llm_context.v1",
                "rollout": decision.as_metadata(),
            },
        )

    def _safe_llm_assistant_text(
        self,
        request: ChatEngineRequest,
        *,
        baseline_state: NutritionConversationState,
        rollout_decision: AIRolloutDecision | None = None,
    ) -> tuple[str, dict]:
        try:
            turn_result = self._llm_turn_result(
                request,
                baseline_state=baseline_state,
                rollout_decision=rollout_decision,
            )
        except Exception as exc:  # pragma: no cover - defensive production boundary
            logger.warning("AI nutrition LLM production fallback: %s", exc)
            return (
                baseline_state.last_assistant_message
                or "No pude obtener una respuesta útil del proveedor externo en modo productivo.",
                {
                    "llm_production_fallback": True,
                    "llm_production_error_type": exc.__class__.__name__,
                },
            )

        assistant_text = turn_result.assistant_text.strip() or (
            baseline_state.last_assistant_message
            or "No pude obtener una respuesta útil del proveedor externo en modo productivo."
        )
        return assistant_text, dict(turn_result.metadata or {})

    def _llm_turn_result(
        self,
        request: ChatEngineRequest,
        *,
        baseline_state: NutritionConversationState,
        rollout_decision: AIRolloutDecision | None = None,
    ) -> ChatEngineTurnResult:
        safe_context = build_safe_llm_context(
            request,
            surface="ai_nutrition_intake",
            conversation_state=baseline_state,
            extra_context={
                "preview_mode": False,
                "production_mode": True,
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


def _replace_last_assistant_message(
    conversation: NutritionConversationState,
    *,
    assistant_text: str,
) -> NutritionConversationState:
    messages = list(conversation.messages)
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].role == "assistant":
            messages[index] = replace(messages[index], text=assistant_text)
            return NutritionConversationState(messages=messages[-12:], result=conversation.result)
    messages.append(NutritionConversationMessage(role="assistant", text=assistant_text))
    return NutritionConversationState(messages=messages[-12:], result=conversation.result)
