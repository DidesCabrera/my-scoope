from django.test import SimpleTestCase

from ai_assistant.application.chat_engines import ChatEngineRequest
from ai_assistant.application.llm_chat_engine import ExternalLLMChatEngine
from ai_assistant.domain import (
    AssistantIntent,
    AssistantMessage,
    AssistantMessageRole,
    AssistantStructuredResponse,
    AssistantToolResult,
    AssistantToolStatus,
)


class ExternalLLMChatEngineToolMetadataTests(SimpleTestCase):
    def test_exposes_controlled_tool_results_to_chat_surface_metadata(self):
        class FakeOrchestrator:
            def continue_turn(self, request):
                return AssistantStructuredResponse(
                    assistant_message=AssistantMessage(
                        role=AssistantMessageRole.ASSISTANT,
                        content="Actualicé la ficha de esta conversación.",
                    ),
                    intent=AssistantIntent(name="capture_nutrition_brief", confidence=0.9),
                    tool_results=(
                        AssistantToolResult(
                            tool_name="update_profile_draft",
                            status=AssistantToolStatus.OK,
                            data={"profile_draft_card": {"title": "Ficha para esta propuesta", "items": []}},
                            metadata={"executor": "profile_draft_tool_executor.v1"},
                        ),
                    ),
                    requires_human_review=False,
                    metadata={"tools_executed": True, "tool_loop_iterations": 1},
                )

        result = ExternalLLMChatEngine(orchestrator=FakeOrchestrator()).continue_chat(
            ChatEngineRequest(message="mido 188", user_id=1)
        )

        self.assertEqual(result.assistant_text, "Actualicé la ficha de esta conversación.")
        self.assertEqual(result.metadata["tool_requests"], 0)
        self.assertTrue(result.metadata["tools_executed"])
        self.assertEqual(result.metadata["tool_results"][0]["tool_name"], "update_profile_draft")
        self.assertEqual(result.metadata["tool_results"][0]["data"]["profile_draft_card"]["title"], "Ficha para esta propuesta")

    def test_forwards_debug_provider_responses_when_present(self):
        class FakeOrchestrator:
            def continue_turn(self, request):
                return AssistantStructuredResponse(
                    assistant_message=AssistantMessage(
                        role=AssistantMessageRole.ASSISTANT,
                        content="Respuesta debug.",
                    ),
                    intent=AssistantIntent(name="answer_question", confidence=0.8),
                    requires_human_review=False,
                    metadata={
                        "debug_provider_responses": [
                            {"provider": "fake", "model": "fake", "response_id": "r1", "text": "raw"}
                        ],
                        "debug_status": "completed",
                    },
                )

        result = ExternalLLMChatEngine(orchestrator=FakeOrchestrator()).continue_chat(
            ChatEngineRequest(message="debug", metadata={"debug_ai_assistant": True})
        )

        self.assertEqual(result.metadata["debug_status"], "completed")
        self.assertEqual(result.metadata["debug_provider_responses"][0]["text"], "raw")
    def test_forwards_safe_structured_contract_diagnostics(self):
        class FakeOrchestrator:
            def continue_turn(self, request):
                return AssistantStructuredResponse(
                    assistant_message=AssistantMessage(
                        role=AssistantMessageRole.ASSISTANT,
                        content="Respuesta reparada.",
                    ),
                    intent=AssistantIntent(name="answer_question", confidence=0.8),
                    requires_human_review=False,
                    metadata={
                        "provider_parse_error": "",
                        "provider_contract_repair_attempted": True,
                        "provider_incomplete_reasons": ["max_output_tokens"],
                        "provider_final_incomplete_reason": "",
                    },
                )

        result = ExternalLLMChatEngine(orchestrator=FakeOrchestrator()).continue_chat(
            ChatEngineRequest(message="hola")
        )

        self.assertTrue(result.metadata["provider_contract_repair_attempted"])
        self.assertEqual(result.metadata["provider_incomplete_reasons"], ["max_output_tokens"])
        self.assertEqual(result.metadata["provider_final_incomplete_reason"], "")

    def test_forwards_safe_provider_and_usage_metadata_to_chat_surface(self):
        class FakeOrchestrator:
            def continue_turn(self, request):
                return AssistantStructuredResponse(
                    assistant_message=AssistantMessage(
                        role=AssistantMessageRole.ASSISTANT,
                        content="Respuesta medida.",
                    ),
                    intent=AssistantIntent(name="answer_question", confidence=0.8),
                    requires_human_review=False,
                    metadata={
                        "usage_observability": {
                            "recorded": True,
                            "provider": "openai",
                            "model": "test-model",
                            "total_tokens": 42,
                        }
                    },
                )

        result = ExternalLLMChatEngine(orchestrator=FakeOrchestrator()).continue_chat(
            ChatEngineRequest(message="hola")
        )

        self.assertEqual(result.metadata["provider"], "openai")
        self.assertEqual(result.metadata["provider_model"], "test-model")
        self.assertTrue(result.metadata["usage_observability"]["recorded"])
        self.assertEqual(result.metadata["usage_observability"]["total_tokens"], 42)
