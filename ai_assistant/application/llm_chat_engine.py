from __future__ import annotations

from ai_assistant.application.chat_engines import ChatEngineRequest, ChatEngineTurnResult
from ai_assistant.application.context_builder import build_safe_llm_context
from ai_assistant.application.orchestrator import ExternalLLMOrchestrator
from ai_assistant.domain import (
    AssistantMessage,
    AssistantMessageRole,
    AssistantTurnRequest,
)


class ExternalLLMChatEngine:
    """ChatEngine adapter around the AI Assistant LLM orchestrator v1.

    This engine is intentionally not wired into the existing nutrition intake
    view by default. It gives future patches a bridge from the shared ChatEngine
    contract to the LLM orchestrator without requiring template or persistence
    changes in Patch 46.
    """

    engine_name = "external_llm_chat_engine_v1"

    def __init__(self, *, orchestrator: ExternalLLMOrchestrator | None = None):
        self.orchestrator = orchestrator or ExternalLLMOrchestrator()

    def continue_chat(self, request: ChatEngineRequest) -> ChatEngineTurnResult:
        safe_context = _safe_context_from_request(request)
        turn_metadata = _assistant_turn_metadata(request, engine_name=self.engine_name)
        structured_response = self.orchestrator.continue_turn(
            AssistantTurnRequest(
                user_message=AssistantMessage(
                    role=AssistantMessageRole.USER,
                    content=request.normalized_message,
                ),
                context=safe_context,
                metadata=turn_metadata,
            )
        )
        return ChatEngineTurnResult(
            state=structured_response,
            assistant_text=structured_response.assistant_text,
            is_ready_for_proposal=structured_response.has_proposals,
            engine_name=self.engine_name,
            metadata={
                "surface": "ai_assistant",
                "mode": "external_llm",
                "requires_human_review": structured_response.requires_human_review,
                "context_builder": safe_context.get("metadata", {}).get("context_builder", ""),
                "tool_requests": len(structured_response.tool_requests),
                "tools_executed": structured_response.metadata.get("tools_executed", False),
                "tool_loop_iterations": structured_response.metadata.get("tool_loop_iterations", 0),
                "audit_version": structured_response.metadata.get("audit_version", ""),
                "audit": structured_response.metadata.get("audit", {}),
            },
        )


def _safe_context_from_request(request: ChatEngineRequest) -> dict:
    metadata = dict(request.metadata or {})
    existing_context = metadata.get("safe_llm_context")
    if isinstance(existing_context, dict):
        return existing_context
    surface = str(metadata.get("surface") or "ai_assistant")
    return build_safe_llm_context(request, surface=surface).as_dict()


def _assistant_turn_metadata(request: ChatEngineRequest, *, engine_name: str) -> dict:
    """Forward safe operational metadata from the chat surface to the orchestrator."""

    request_metadata = dict(request.metadata or {})
    metadata = {
        "chat_engine": engine_name,
        "tool_user": request_metadata.get("tool_user")
        or request_metadata.get("user")
        or request_metadata.get("current_user"),
    }
    for key in (
        "action_type",
        "ai_action_type",
        "surface",
        "conversation_id",
        "turn_id",
        "chat_engine_mode",
        "rollout",
    ):
        if key in request_metadata:
            metadata[key] = request_metadata[key]
    return metadata
