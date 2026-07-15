"""Explicit deterministic runtime for the nutrition-intake chat surface.

The class in this module is the only chat engine allowed to run the legacy
semantic parsers, pending-field state and question-selection policy. LLM modes
may select this engine as an explicit rollout fallback, but they must not call
its conversational helpers as co-authoring logic within an LLM turn.
"""

from __future__ import annotations

from ai_assistant.application.chat_engines import (
    ChatEngineRequest,
    ChatEngineTurnResult,
)
from notas.application.ai_intake.nutrition_brief import start_or_continue_conversation

DETERMINISTIC_ENGINE_MODE = "deterministic"


class DeterministicNutritionIntakeChatEngine:
    """Adapter for the isolated rule-based nutrition-intake runtime."""

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
                "mode": DETERMINISTIC_ENGINE_MODE,
                "conversation_policy": "deterministic_runtime",
            },
        )
