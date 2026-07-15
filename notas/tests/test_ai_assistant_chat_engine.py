from django.test import SimpleTestCase, override_settings

from ai_assistant.application.chat_engines import ChatEngineRequest, ChatEngineTurnResult
from notas.application.ai_intake.chat_engine import (
    AI_ASSISTANT_CHAT_ENGINE_DETERMINISTIC,
    AI_ASSISTANT_CHAT_ENGINE_LLM_PREVIEW,
    DeterministicNutritionIntakeChatEngine,
    LLMPreviewNutritionIntakeChatEngine,
    get_nutrition_intake_chat_engine,
    get_nutrition_intake_chat_engine_mode,
)
from notas.application.ai_intake.nutrition_brief import serialize_conversation


class DeterministicNutritionIntakeChatEngineTests(SimpleTestCase):
    def test_engine_wraps_current_intake_flow(self):
        engine = get_nutrition_intake_chat_engine()

        result = engine.continue_chat(
            ChatEngineRequest(message="Quiero un plan simple de 2200 kcal")
        )

        self.assertEqual(result.engine_name, "deterministic_nutrition_intake")
        self.assertEqual(result.metadata["surface"], "ai_nutrition_intake")
        self.assertEqual(result.metadata["mode"], AI_ASSISTANT_CHAT_ENGINE_DETERMINISTIC)
        self.assertTrue(result.assistant_text)
        self.assertEqual(result.state.messages[-2].role, "user")
        self.assertEqual(result.state.messages[-1].role, "assistant")

    def test_engine_can_continue_existing_payload(self):
        engine = get_nutrition_intake_chat_engine()
        first_turn = engine.continue_chat(
            ChatEngineRequest(message="Quiero bajar grasa con 4 comidas")
        )

        second_turn = engine.continue_chat(
            ChatEngineRequest(
                message="Entreno 3 veces por semana",
                existing_payload=serialize_conversation(first_turn.state),
            )
        )

        self.assertEqual(second_turn.engine_name, "deterministic_nutrition_intake")
        self.assertGreaterEqual(len(second_turn.state.messages), 4)


class NutritionIntakeChatEngineSelectorTests(SimpleTestCase):
    @override_settings(AI_ASSISTANT_CHAT_ENGINE_MODE="deterministic")
    def test_default_selector_returns_deterministic_engine(self):
        self.assertEqual(get_nutrition_intake_chat_engine_mode(), "deterministic")
        self.assertIsInstance(get_nutrition_intake_chat_engine(), DeterministicNutritionIntakeChatEngine)

    @override_settings(AI_ASSISTANT_CHAT_ENGINE_MODE="llm_preview")
    def test_selector_can_return_llm_preview_engine_by_explicit_setting(self):
        self.assertEqual(get_nutrition_intake_chat_engine_mode(), "llm_preview")
        self.assertIsInstance(get_nutrition_intake_chat_engine(), LLMPreviewNutritionIntakeChatEngine)

    @override_settings(AI_ASSISTANT_CHAT_ENGINE_MODE="unknown_mode")
    def test_selector_falls_back_to_deterministic_for_unknown_mode(self):
        self.assertEqual(get_nutrition_intake_chat_engine_mode(), "deterministic")
        self.assertIsInstance(get_nutrition_intake_chat_engine(), DeterministicNutritionIntakeChatEngine)

    def test_llm_preview_preserves_nutrition_conversation_state_shape(self):
        class StubLLMEngine:
            engine_name = "stub_llm"

            def __init__(self):
                self.requests = []

            def continue_chat(self, request):
                self.requests.append(request)
                return ChatEngineTurnResult(
                    state={"external": True},
                    assistant_text="Respuesta preview desde LLM.",
                    engine_name=self.engine_name,
                    metadata={"tools_executed": False},
                )

        stub_llm_engine = StubLLMEngine()
        engine = LLMPreviewNutritionIntakeChatEngine(llm_engine=stub_llm_engine)

        result = engine.continue_chat(
            ChatEngineRequest(message="Quiero un plan de 2100 kcal con 4 comidas", user_id=1)
        )

        self.assertEqual(result.engine_name, "llm_preview_nutrition_intake")
        self.assertEqual(result.metadata["mode"], AI_ASSISTANT_CHAT_ENGINE_LLM_PREVIEW)
        self.assertFalse(result.metadata["llm_tools_executed"])
        self.assertEqual(result.assistant_text, "Respuesta preview desde LLM.")
        self.assertEqual(result.state.messages[-2].role, "user")
        self.assertEqual(result.state.messages[-1].role, "assistant")
        self.assertEqual(result.state.last_assistant_message, "Respuesta preview desde LLM.")
        self.assertIsNone(result.state.result.brief.calorie_target)
        self.assertTrue(result.metadata["deterministic_coauthor_disabled"])
        safe_context = stub_llm_engine.requests[0].metadata["safe_llm_context"]
        self.assertEqual(safe_context["metadata"]["context_builder"], "safe_llm_context.v1")
        self.assertNotIn("calorie_target", safe_context.get("nutrition_brief", {}))
        self.assertTrue(safe_context["runtime"]["tools_enabled"])

class NutritionIntakeLLMPreviewPatch58Tests(SimpleTestCase):
    def test_llm_preview_marks_usage_action_type_for_observability(self):
        class StubLLMEngine:
            engine_name = "stub_llm"

            def __init__(self):
                self.requests = []

            def continue_chat(self, request):
                self.requests.append(request)
                return ChatEngineTurnResult(
                    state={"external": True},
                    assistant_text="Respuesta medida desde preview.",
                    engine_name=self.engine_name,
                    metadata={
                        "provider": "fake",
                        "provider_model": "fake-llm",
                        "tool_requests": 0,
                        "tools_executed": False,
                        "usage_observability": {"recorded": True},
                    },
                )

        stub_llm_engine = StubLLMEngine()
        engine = LLMPreviewNutritionIntakeChatEngine(llm_engine=stub_llm_engine)

        result = engine.continue_chat(
            ChatEngineRequest(
                message="Quiero 2200 kcal con 4 comidas",
                user_id=1,
                metadata={"conversation_id": "15", "turn_id": "turn-1"},
            )
        )

        self.assertEqual(result.assistant_text, "Respuesta medida desde preview.")
        self.assertFalse(result.metadata["llm_preview_fallback"])
        self.assertEqual(result.metadata["llm_provider"], "fake")
        preview_metadata = stub_llm_engine.requests[0].metadata
        self.assertEqual(preview_metadata["action_type"], "assistant.ai_nutrition_intake.preview")
        self.assertEqual(preview_metadata["conversation_id"], "15")
        self.assertEqual(preview_metadata["turn_id"], "turn-1")
        self.assertEqual(preview_metadata["safe_llm_context"]["metadata"]["preview_mode"], True)

    def test_llm_preview_forwards_structured_provider_contract_diagnostics(self):
        class StubLLMEngine:
            engine_name = "stub_llm"

            def continue_chat(self, request):
                return ChatEngineTurnResult(
                    state={"external": True},
                    assistant_text="Respuesta reparada.",
                    engine_name=self.engine_name,
                    metadata={
                        "provider": "openai",
                        "provider_model": "gpt-test",
                        "provider_parse_error": "",
                        "provider_contract_repair_attempted": True,
                        "provider_incomplete_reasons": ["max_output_tokens"],
                        "provider_final_incomplete_reason": "",
                        "usage_observability": {"recorded": True},
                    },
                )

        result = LLMPreviewNutritionIntakeChatEngine(llm_engine=StubLLMEngine()).continue_chat(
            ChatEngineRequest(message="hola", user_id=1)
        )

        self.assertTrue(result.metadata["llm_provider_contract_repair_attempted"])
        self.assertEqual(
            result.metadata["llm_provider_incomplete_reasons"],
            ["max_output_tokens"],
        )
        self.assertEqual(result.metadata["llm_provider_final_incomplete_reason"], "")

    def test_llm_preview_exposes_safe_semantic_and_tool_result_summaries(self):
        class StubLLMEngine:
            engine_name = "stub_llm"

            def continue_chat(self, request):
                return ChatEngineTurnResult(
                    state={"external": True},
                    assistant_text="Registré tu ficha temporal.",
                    engine_name=self.engine_name,
                    metadata={
                        "semantic_intent": "capture_nutrition_brief",
                        "semantic_missing_slots": ["goal", "goal", "meals_per_day"],
                        "tool_results": [
                            {
                                "tool_name": "update_profile_draft",
                                "status": "ok",
                                "data": {"profile_draft": {"weight_kg": 85}},
                            },
                            {
                                "tool_name": "read_proposal",
                                "status": "error",
                                "error_code": "proposal_not_found",
                                "error_message": "Internal detail must not be forwarded.",
                            },
                        ],
                        "tools_executed": True,
                    },
                )

        result = LLMPreviewNutritionIntakeChatEngine(llm_engine=StubLLMEngine()).continue_chat(
            ChatEngineRequest(message="Usa estos datos", user_id=1)
        )

        self.assertEqual(result.metadata["llm_semantic_intent"], "capture_nutrition_brief")
        self.assertEqual(result.metadata["llm_semantic_missing_slots"], ["goal", "meals_per_day"])
        self.assertEqual(
            result.metadata["llm_tool_results"],
            [
                {"tool_name": "update_profile_draft", "status": "ok"},
                {
                    "tool_name": "read_proposal",
                    "status": "error",
                    "error_code": "proposal_not_found",
                },
            ],
        )
        self.assertNotIn("data", result.metadata["llm_tool_results"][0])
        self.assertNotIn("error_message", result.metadata["llm_tool_results"][1])

    def test_llm_preview_falls_back_to_baseline_text_on_unexpected_error(self):
        class BrokenLLMEngine:
            engine_name = "broken_llm"

            def continue_chat(self, request):
                raise RuntimeError("boom")

        engine = LLMPreviewNutritionIntakeChatEngine(llm_engine=BrokenLLMEngine())

        result = engine.continue_chat(
            ChatEngineRequest(message="Quiero bajar grasa con 4 comidas", user_id=1)
        )

        self.assertTrue(result.assistant_text)
        self.assertTrue(result.metadata["llm_preview_fallback"])
        self.assertEqual(result.state.messages[-1].role, "assistant")

    @override_settings(AI_ASSISTANT_CHAT_ENGINE_MODE="llm_preview", AI_ASSISTANT_LLM_PROVIDER="fake")
    def test_engine_status_exposes_preview_guardrails_and_observability(self):
        from notas.application.ai_intake.chat_engine import build_ai_nutrition_intake_engine_status

        status = build_ai_nutrition_intake_engine_status()

        self.assertEqual(status["mode"], "llm_preview")
        self.assertEqual(status["label"], "LLM preview")
        self.assertTrue(status["is_llm_preview"])
        self.assertTrue(status["observability_enabled"])
        self.assertTrue(status["guardrails_enabled"])
        self.assertEqual(status["provider"], "fake")


class NutritionIntakeLLMProductionPatch62Tests(SimpleTestCase):
    @override_settings(AI_ASSISTANT_CHAT_ENGINE_MODE="llm_production")
    def test_selector_can_return_llm_production_engine(self):
        from notas.application.ai_intake.chat_engine import (
            AI_ASSISTANT_CHAT_ENGINE_LLM_PRODUCTION,
            LLMProductionNutritionIntakeChatEngine,
        )

        self.assertEqual(get_nutrition_intake_chat_engine_mode(), AI_ASSISTANT_CHAT_ENGINE_LLM_PRODUCTION)
        self.assertIsInstance(get_nutrition_intake_chat_engine(), LLMProductionNutritionIntakeChatEngine)

    @override_settings(
        AI_ASSISTANT_CHAT_ENGINE_MODE="llm_production",
        AI_ASSISTANT_LLM_ROLLOUT_ENABLED=False,
        AI_ASSISTANT_LLM_ROLLOUT_MODE="all",
    )
    def test_llm_production_falls_back_to_deterministic_when_rollout_disabled(self):
        from notas.application.ai_intake.chat_engine import LLMProductionNutritionIntakeChatEngine

        class StubLLMEngine:
            engine_name = "stub_llm"

            def continue_chat(self, request):  # pragma: no cover - must not be called
                raise AssertionError("LLM should not be called when rollout blocks")

        engine = LLMProductionNutritionIntakeChatEngine(llm_engine=StubLLMEngine())

        result = engine.continue_chat(ChatEngineRequest(message="Quiero 2200 kcal", user_id=1))

        self.assertEqual(result.engine_name, "deterministic_nutrition_intake")
        self.assertEqual(result.metadata["requested_mode"], "llm_production")
        self.assertTrue(result.metadata["llm_production_fallback"])
        self.assertEqual(result.metadata["rollout"]["reason"], "rollout_disabled")

    @override_settings(
        AI_ASSISTANT_CHAT_ENGINE_MODE="llm_production",
        AI_ASSISTANT_LLM_ROLLOUT_ENABLED=True,
        AI_ASSISTANT_LLM_ROLLOUT_MODE="allowlist",
        AI_ASSISTANT_LLM_ROLLOUT_USER_IDS="1",
    )
    def test_llm_production_calls_llm_for_allowlisted_user_with_production_action_type(self):
        from notas.application.ai_intake.chat_engine import LLMProductionNutritionIntakeChatEngine

        class StubLLMEngine:
            engine_name = "stub_llm"

            def __init__(self):
                self.requests = []

            def continue_chat(self, request):
                self.requests.append(request)
                return ChatEngineTurnResult(
                    state={"external": True},
                    assistant_text="Respuesta productiva controlada.",
                    engine_name=self.engine_name,
                    metadata={
                        "provider": "fake",
                        "provider_model": "fake-production-model",
                        "tool_requests": 0,
                        "tools_executed": False,
                        "usage_observability": {"recorded": True},
                    },
                )

        stub_llm_engine = StubLLMEngine()
        engine = LLMProductionNutritionIntakeChatEngine(llm_engine=stub_llm_engine)

        result = engine.continue_chat(
            ChatEngineRequest(
                message="Quiero 2200 kcal con 4 comidas",
                user_id=1,
                metadata={"conversation_id": "55", "turn_id": "turn-prod-1"},
            )
        )

        self.assertEqual(result.engine_name, "llm_production_nutrition_intake")
        self.assertEqual(result.assistant_text, "Respuesta productiva controlada.")
        self.assertTrue(result.metadata["llm_production_enabled"])
        self.assertEqual(result.metadata["rollout"]["reason"], "rollout_allowlist")
        production_metadata = stub_llm_engine.requests[0].metadata
        self.assertEqual(production_metadata["action_type"], "assistant.ai_nutrition_intake.production")
        self.assertEqual(production_metadata["chat_engine_mode"], "llm_production")
        self.assertEqual(production_metadata["conversation_id"], "55")
        self.assertEqual(production_metadata["turn_id"], "turn-prod-1")
        self.assertEqual(production_metadata["safe_llm_context"]["metadata"]["production_mode"], True)

    @override_settings(
        AI_ASSISTANT_CHAT_ENGINE_MODE="llm_production",
        AI_ASSISTANT_LLM_ROLLOUT_ENABLED=True,
        AI_ASSISTANT_LLM_ROLLOUT_MODE="all",
    )
    def test_engine_status_exposes_production_rollout_state(self):
        from notas.application.ai_intake.chat_engine import build_ai_nutrition_intake_engine_status

        status = build_ai_nutrition_intake_engine_status()

        self.assertEqual(status["mode"], "llm_production")
        self.assertEqual(status["label"], "LLM producción")
        self.assertTrue(status["is_llm_production"])
        self.assertTrue(status["rollout_enabled"])
        self.assertEqual(status["rollout_mode"], "all")


class NutritionIntakeVisibleBoundaryTests(SimpleTestCase):
    def test_llm_preview_never_persists_raw_structured_json_as_visible_text(self):
        class StubLLMEngine:
            engine_name = "stub_llm"

            def continue_chat(self, request):
                return ChatEngineTurnResult(
                    state={"external": True},
                    assistant_text=(
                        '{"intent":{"name":"capture_nutrition_brief"},'
                        '"assistant_message":{"content":"Puedo ayudarte con una propuesta inicial.\\n\\n¿Qué objetivo quieres?"},'
                        '"requires_human_review":true,'
                        '"tool_requests":[{"tool_name":"update_proposal_preferences","arguments":{"updates":{"requested_entity":"daily_plan"}}}]}'
                    ),
                    engine_name=self.engine_name,
                    metadata={"tools_executed": False},
                )

        result = LLMPreviewNutritionIntakeChatEngine(llm_engine=StubLLMEngine()).continue_chat(
            ChatEngineRequest(message="Quiero una dieta", user_id=1)
        )

        self.assertEqual(
            result.assistant_text,
            "Puedo ayudarte con una propuesta inicial.\n\n¿Qué objetivo quieres?",
        )
        self.assertEqual(result.state.last_assistant_message, result.assistant_text)
        self.assertNotIn('"intent"', result.state.last_assistant_message)
        self.assertNotIn('"tool_requests"', result.state.last_assistant_message)
        self.assertTrue(result.metadata["llm_visible_text_extracted"])

    def test_llm_preview_extracts_embedded_structured_json(self):
        class StubLLMEngine:
            engine_name = "stub_llm"

            def continue_chat(self, request):
                return ChatEngineTurnResult(
                    state={"external": True},
                    assistant_text=(
                        'debug envelope: {"assistant_message":{"content":"Texto humano."},'
                        '"tool_requests":[]} trailing text'
                    ),
                    engine_name=self.engine_name,
                    metadata={"tools_executed": False},
                )

        result = LLMPreviewNutritionIntakeChatEngine(llm_engine=StubLLMEngine()).continue_chat(
            ChatEngineRequest(message="Hola", user_id=1)
        )

        self.assertEqual(result.assistant_text, "Texto humano.")
        self.assertEqual(result.state.last_assistant_message, "Texto humano.")
