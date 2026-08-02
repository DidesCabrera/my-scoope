from django.test import SimpleTestCase, override_settings

from ai_assistant.application.chat_engines import ChatEngineRequest, ChatEngineTurnResult
from notas.application.ai_intake.chat_engine import (
    AI_ASSISTANT_CHAT_ENGINE_LLM,
    LLMNutritionIntakeChatEngine,
    LLMPreviewNutritionIntakeChatEngine,
    LLMProductionNutritionIntakeChatEngine,
    build_ai_nutrition_intake_engine_status,
    get_nutrition_intake_chat_engine,
    get_nutrition_intake_chat_engine_mode,
)


class StubLLMEngine:
    engine_name = "stub_llm"

    def __init__(self, *, text="Respuesta natural desde el asistente.", metadata=None):
        self.text = text
        self.metadata = dict(metadata or {})
        self.requests = []

    def continue_chat(self, request):
        self.requests.append(request)
        return ChatEngineTurnResult(
            state={"external": True},
            assistant_text=self.text,
            engine_name=self.engine_name,
            metadata=self.metadata,
        )


class NutritionIntakeUnifiedEngineTests(SimpleTestCase):
    @override_settings(AI_ASSISTANT_CHAT_ENGINE_MODE="llm")
    def test_selector_returns_the_unified_llm_engine(self):
        self.assertEqual(get_nutrition_intake_chat_engine_mode(), AI_ASSISTANT_CHAT_ENGINE_LLM)
        self.assertIsInstance(get_nutrition_intake_chat_engine(), LLMNutritionIntakeChatEngine)

    def test_legacy_and_unknown_modes_cannot_reactivate_the_deterministic_runtime(self):
        for legacy_mode in ("deterministic", "llm_preview", "llm_production", "unknown"):
            with self.subTest(legacy_mode=legacy_mode):
                with self.settings(AI_ASSISTANT_CHAT_ENGINE_MODE=legacy_mode):
                    self.assertEqual(
                        get_nutrition_intake_chat_engine_mode(),
                        AI_ASSISTANT_CHAT_ENGINE_LLM,
                    )
                    self.assertIsInstance(
                        get_nutrition_intake_chat_engine(),
                        LLMNutritionIntakeChatEngine,
                    )

    def test_legacy_engine_class_names_are_safe_aliases_without_rollout_fallback(self):
        stub = StubLLMEngine(text="Resultado unificado.")

        preview_result = LLMPreviewNutritionIntakeChatEngine(llm_engine=stub).continue_chat(
            ChatEngineRequest(message="Hola", user_id=1)
        )
        production_result = LLMProductionNutritionIntakeChatEngine(
            llm_engine=stub
        ).continue_chat(ChatEngineRequest(message="Hola otra vez", user_id=1))

        self.assertEqual(preview_result.engine_name, "llm_nutrition_intake")
        self.assertEqual(production_result.engine_name, "llm_nutrition_intake")
        self.assertFalse(preview_result.metadata["deterministic_runtime_invoked"])
        self.assertFalse(production_result.metadata["deterministic_runtime_invoked"])

    def test_engine_preserves_typed_conversation_state_and_builds_workspace(self):
        stub = StubLLMEngine(text="Prepararé una propuesta con lo que ya sé.")
        engine = LLMNutritionIntakeChatEngine(llm_engine=stub)

        result = engine.continue_chat(
            ChatEngineRequest(
                message="Quiero perder grasa con un plan simple",
                user_id=1,
            )
        )

        self.assertEqual(result.engine_name, "llm_nutrition_intake")
        self.assertEqual(result.metadata["mode"], "llm")
        self.assertEqual(result.state.messages[-2].role, "user")
        self.assertEqual(result.state.messages[-1].role, "assistant")
        self.assertEqual(result.state.last_assistant_message, result.assistant_text)
        self.assertTrue(result.metadata["deterministic_coauthor_disabled"])
        workspace = stub.requests[0].metadata["safe_llm_context"]
        self.assertEqual(workspace["surface"], "ai_nutrition_intake")
        self.assertEqual(
            workspace["metadata"]["tool_oriented_intake"]["version"],
            "ai_assistant_workspace.v1",
        )
        self.assertNotIn("recent_messages", str(workspace))

    def test_engine_sets_unified_action_metadata_and_preserves_turn_identity(self):
        stub = StubLLMEngine(
            metadata={
                "provider": "openai",
                "provider_model": "gpt-test",
                "tools_executed": False,
                "usage_observability": {"recorded": True},
            }
        )

        result = LLMNutritionIntakeChatEngine(llm_engine=stub).continue_chat(
            ChatEngineRequest(
                message="Quiero una propuesta",
                user_id=1,
                metadata={"conversation_id": "15", "turn_id": "turn-1"},
            )
        )

        request_metadata = stub.requests[0].metadata
        self.assertEqual(request_metadata["action_type"], "assistant.ai_nutrition_intake")
        self.assertEqual(request_metadata["chat_engine_mode"], "llm")
        self.assertEqual(request_metadata["conversation_id"], "15")
        self.assertEqual(request_metadata["turn_id"], "turn-1")
        self.assertEqual(result.metadata["llm_provider"], "openai")

    def test_provider_failure_never_invokes_the_old_interviewer(self):
        class BrokenLLMEngine:
            engine_name = "broken"

            def continue_chat(self, request):
                raise RuntimeError("boom")

        result = LLMNutritionIntakeChatEngine(
            llm_engine=BrokenLLMEngine()
        ).continue_chat(ChatEngineRequest(message="Quiero una propuesta", user_id=1))

        self.assertTrue(result.metadata["llm_degraded"])
        self.assertEqual(result.metadata["llm_degraded_reason"], "provider_failure")
        self.assertFalse(result.metadata["deterministic_runtime_invoked"])
        self.assertIn("No hice ningún cambio", result.assistant_text)

    @override_settings(
        AI_ASSISTANT_CHAT_ENGINE_MODE="llm",
        AI_ASSISTANT_LLM_PROVIDER="openai",
        AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS=True,
    )
    def test_status_reports_one_active_assistant(self):
        status = build_ai_nutrition_intake_engine_status()

        self.assertEqual(status["mode"], "llm")
        self.assertEqual(status["label"], "AI activo")
        self.assertTrue(status["is_active"])
        self.assertTrue(status["proposal_tools_enabled"])


class NutritionIntakeVisibleBoundaryTests(SimpleTestCase):
    def test_legacy_json_envelopes_are_not_persisted_as_visible_text(self):
        stub = StubLLMEngine(
            text=(
                '{"intent":{"name":"capture_nutrition_brief"},'
                '"assistant_message":{"content":"Puedo preparar una propuesta.\\n\\n¿Cuál es tu objetivo?"},'
                '"requires_human_review":true,"tool_requests":[]}'
            )
        )

        result = LLMNutritionIntakeChatEngine(llm_engine=stub).continue_chat(
            ChatEngineRequest(message="Quiero una dieta", user_id=1)
        )

        self.assertEqual(
            result.assistant_text,
            "Puedo preparar una propuesta.\n\n¿Cuál es tu objetivo?",
        )
        self.assertNotIn('"intent"', result.state.last_assistant_message)
        self.assertTrue(result.metadata["llm_visible_text_extracted"])

    def test_embedded_legacy_envelope_is_also_safely_unwrapped(self):
        stub = StubLLMEngine(
            text=(
                'debug envelope: {"assistant_message":{"content":"Texto humano."},'
                '"tool_requests":[]} trailing'
            )
        )

        result = LLMNutritionIntakeChatEngine(llm_engine=stub).continue_chat(
            ChatEngineRequest(message="Hola", user_id=1)
        )

        self.assertEqual(result.assistant_text, "Texto humano.")
