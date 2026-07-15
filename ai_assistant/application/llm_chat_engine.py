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
                "semantic_intent": structured_response.intent.name.value,
                "semantic_missing_slots": list(structured_response.intent.missing_slots),
                "tool_requests": len(structured_response.tool_requests),
                "tools_executed": structured_response.metadata.get("tools_executed", False),
                "tool_loop_iterations": structured_response.metadata.get("tool_loop_iterations", 0),
                "tool_results": _safe_tool_results_for_chat_metadata(structured_response.tool_results),
                "audit_version": structured_response.metadata.get("audit_version", ""),
                "audit": structured_response.metadata.get("audit", {}),
                **_operational_metadata_for_chat_surface(structured_response.metadata),
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


def _safe_tool_results_for_chat_metadata(tool_results) -> list[dict]:
    """Expose bounded local tool results to chat-surface adapters.

    This metadata is not sent back to the provider. It lets My Scoope render
    controlled tool outputs, such as profile cards, as real chat objects instead
    of depending on the LLM to describe them in text.
    """

    safe_results: list[dict] = []
    for result in tuple(tool_results or ()):  # provider-agnostic AssistantToolResult
        payload = result.as_dict()
        safe_results.append(
            {
                "tool_name": payload.get("tool_name", ""),
                "status": payload.get("status", ""),
                "request_id": payload.get("request_id", ""),
                "error_code": payload.get("error_code", ""),
                "data": dict(payload.get("data") or {}),
                "metadata": dict(payload.get("metadata") or {}),
            }
        )
    return safe_results


def _operational_metadata_for_chat_surface(metadata: dict) -> dict:
    """Forward safe provider/usage metadata plus explicit debug traces.

    Provider/model/usage are operational facts already persisted by the usage
    recorder. Keeping them on the ChatEngine result lets the nutrition surface
    and CM24 validator distinguish a real provider turn from a technical
    fallback without exposing prompts, tool arguments or raw provider payloads.
    """

    usage = dict(metadata.get("usage_observability") or {})
    payload = {
        "provider": str(usage.get("provider") or metadata.get("provider") or ""),
        "provider_model": str(usage.get("model") or metadata.get("provider_model") or ""),
        "usage_observability": usage,
    }
    debug_keys = (
        "debug_provider_responses",
        "debug_status",
        "debug_error_type",
        "provider_parse_error",
        "provider_contract_repair_attempted",
        "provider_incomplete_reasons",
        "provider_final_incomplete_reason",
        "provider_response_was_json",
        "provider_response_jsonish_content_extracted",
        "provider_native_tool_transport",
        "provider_native_tool_calls",
        "provider_text_parse_ignored_due_to_native_tools",
        "tool_followup_local_ack",
        "tool_followup_local_ack_policy",
        "post_tool_degraded",
        "post_tool_degradation_reason",
        "provider_tool_followup_failed",
        "provider_tool_followup_error_type",
        "provider_tool_followup_error_status",
        "provider_tool_followup_error_provider_type",
        "provider_tool_followup_error_code",
        "provider_tool_followup_error_message",
        "provider_tool_followup_error_param",
        "provider_tool_followup_error_request_id",
    )
    payload.update({key: metadata[key] for key in debug_keys if key in metadata})
    return payload
