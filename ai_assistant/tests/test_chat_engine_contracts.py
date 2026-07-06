from django.test import SimpleTestCase

from ai_assistant.application.chat_engines import (
    ChatEngineRequest,
    ChatEngineTurnResult,
)


class ChatEngineContractsTests(SimpleTestCase):
    def test_request_normalizes_user_message(self):
        request = ChatEngineRequest(message="  quiero   un plan   simple  ")

        self.assertEqual(request.normalized_message, "quiero un plan simple")

    def test_turn_result_keeps_engine_metadata(self):
        result = ChatEngineTurnResult(
            state={"ok": True},
            assistant_text="Listo.",
            is_ready_for_proposal=True,
            engine_name="fake_engine",
            metadata={"surface": "test"},
        )

        self.assertEqual(result.engine_name, "fake_engine")
        self.assertTrue(result.is_ready_for_proposal)
        self.assertEqual(result.metadata["surface"], "test")

    def test_ai_assistant_contracts_do_not_import_food_catalog(self):
        import ai_assistant.application.chat_engines as chat_engines

        self.assertNotIn("food_catalog", chat_engines.__dict__)


class ExternalLLMChatEngineMetadataForwardingTests(SimpleTestCase):
    def test_forwards_safe_action_and_turn_metadata_to_orchestrator(self):
        from ai_assistant.application.llm_chat_engine import ExternalLLMChatEngine
        from ai_assistant.domain import AssistantMessage, AssistantMessageRole, AssistantStructuredResponse

        class StubOrchestrator:
            def __init__(self):
                self.requests = []

            def continue_turn(self, request):
                self.requests.append(request)
                return AssistantStructuredResponse(
                    assistant_message=AssistantMessage(
                        role=AssistantMessageRole.ASSISTANT,
                        content="ok",
                    )
                )

        orchestrator = StubOrchestrator()
        engine = ExternalLLMChatEngine(orchestrator=orchestrator)

        result = engine.continue_chat(
            ChatEngineRequest(
                message="hola",
                user_id=1,
                metadata={
                    "action_type": "assistant.ai_nutrition_intake.production",
                    "conversation_id": "99",
                    "turn_id": "turn-99",
                    "chat_engine_mode": "llm_production",
                    "surface": "ai_nutrition_intake",
                },
            )
        )

        self.assertEqual(result.assistant_text, "ok")
        forwarded = orchestrator.requests[0].metadata
        self.assertEqual(forwarded["action_type"], "assistant.ai_nutrition_intake.production")
        self.assertEqual(forwarded["conversation_id"], "99")
        self.assertEqual(forwarded["turn_id"], "turn-99")
        self.assertEqual(forwarded["chat_engine_mode"], "llm_production")
        self.assertEqual(forwarded["surface"], "ai_nutrition_intake")
