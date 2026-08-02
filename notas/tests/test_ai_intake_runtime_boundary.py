from django.test import SimpleTestCase, override_settings

from ai_assistant.application.chat_engines import ChatEngineRequest, ChatEngineTurnResult
from notas.application.ai_intake.chat_engine import (
    LLMPreviewNutritionIntakeChatEngine,
    LLMProductionNutritionIntakeChatEngine,
    _apply_llm_tool_results_to_conversation_state,
)
from notas.application.ai_intake.deterministic_chat_engine import (
    DeterministicNutritionIntakeChatEngine,
)
from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    NutritionConversationMessage,
    NutritionConversationState,
    build_intake_result_from_brief,
    build_llm_intake_result_from_brief,
    required_proposal_fields,
)


class AiIntakeRuntimeBoundaryTests(SimpleTestCase):
    def test_deterministic_and_llm_state_builders_have_distinct_conversation_policy(self):
        brief = NutritionBrief(raw_prompt="quiero una dieta")

        deterministic = build_intake_result_from_brief(brief)
        llm_state = build_llm_intake_result_from_brief(brief)

        self.assertEqual(deterministic.brief.pending_field, "goal")
        self.assertTrue(deterministic.visible_follow_up_questions)
        self.assertTrue(deterministic.required_follow_up_questions)

        self.assertIsNone(llm_state.brief.pending_field)
        self.assertEqual(llm_state.follow_up_questions, [])
        self.assertEqual(llm_state.required_follow_up_questions, [])
        self.assertEqual(llm_state.visible_follow_up_questions, [])
        self.assertTrue(llm_state.has_required_pending_questions)
        self.assertFalse(llm_state.is_ready_for_proposal)
        self.assertEqual(
            required_proposal_fields(llm_state.brief),
            [
                "goal",
                "weight_kg",
                "height_cm",
                "age_years",
                "sex",
                "activity_level",
            ],
        )

    def test_llm_tool_sync_rebuilds_state_without_pending_question_policy(self):
        conversation = NutritionConversationState(
            messages=[NutritionConversationMessage(role="user", text="Quiero ganar masa")],
            result=build_intake_result_from_brief(NutritionBrief(raw_prompt="Quiero ganar masa")),
        )
        metadata = {
            "tool_results": [
                {
                    "tool_name": "update_proposal_preferences",
                    "status": "ok",
                    "data": {
                        "proposal_preferences": {
                            "goal": "muscle_gain",
                            "meals_per_day": 4,
                            "field_sources": {
                                "goal": "chat_draft",
                                "meals_per_day": "chat_draft",
                            },
                        }
                    },
                }
            ]
        }

        updated, applied_count = _apply_llm_tool_results_to_conversation_state(
            conversation,
            metadata,
        )

        self.assertEqual(applied_count, 1)
        self.assertEqual(updated.result.brief.goal, "muscle_gain")
        self.assertEqual(updated.result.brief.meals_per_day, 4)
        self.assertIsNone(updated.result.brief.pending_field)
        self.assertEqual(updated.result.follow_up_questions, [])
        self.assertEqual(updated.result.visible_follow_up_questions, [])
        self.assertFalse(updated.result.is_ready_for_proposal)

    def test_preview_provider_failure_returns_technical_message_without_running_deterministic_parser(self):
        class BrokenLLMEngine:
            engine_name = "broken_llm"

            def continue_chat(self, request):
                raise RuntimeError("boom")

        result = LLMPreviewNutritionIntakeChatEngine(
            llm_engine=BrokenLLMEngine()
        ).continue_chat(
            ChatEngineRequest(
                message="Quiero bajar grasa, peso 85 kg y mido 188 cm",
                user_id=1,
            )
        )

        self.assertTrue(result.metadata["llm_degraded"])
        self.assertEqual(result.metadata["llm_degraded_reason"], "provider_failure")
        self.assertFalse(result.metadata["deterministic_runtime_invoked"])
        self.assertEqual(result.metadata["conversation_policy"], "llm_tools")
        self.assertIsNone(result.state.result.brief.goal)
        self.assertIsNone(result.state.result.brief.weight_kg)
        self.assertIsNone(result.state.result.brief.height_cm)
        self.assertIsNone(result.state.result.brief.pending_field)

    def test_legacy_production_name_uses_the_same_llm_without_rollout_boundary(self):
        class StubLLMEngine:
            engine_name = "stub"

            def continue_chat(self, request):
                return ChatEngineTurnResult(
                    state={},
                    assistant_text="Resultado del asistente único.",
                    engine_name=self.engine_name,
                    metadata={"tools_executed": False},
                )

        result = LLMProductionNutritionIntakeChatEngine(
            llm_engine=StubLLMEngine()
        ).continue_chat(
            ChatEngineRequest(message="Quiero bajar grasa", user_id=1)
        )

        self.assertEqual(result.engine_name, "llm_nutrition_intake")
        self.assertEqual(result.metadata["conversation_policy"], "llm_tools")
        self.assertFalse(result.metadata["deterministic_runtime_invoked"])
        self.assertIsNone(result.state.result.brief.goal)
        self.assertIsNone(result.state.result.brief.pending_field)

    def test_successful_llm_turn_does_not_parse_user_message_outside_tools(self):
        class EchoLLMEngine:
            engine_name = "echo_llm"

            def continue_chat(self, request):
                return ChatEngineTurnResult(
                    state={},
                    assistant_text="Entendido.",
                    engine_name=self.engine_name,
                    metadata={"tools_executed": False},
                )

        result = LLMPreviewNutritionIntakeChatEngine(
            llm_engine=EchoLLMEngine()
        ).continue_chat(
            ChatEngineRequest(
                message="Quiero bajar grasa, peso 85 kg y haré 4 comidas",
                user_id=1,
            )
        )

        self.assertEqual(result.assistant_text, "Entendido.")
        self.assertEqual(result.metadata["conversation_policy"], "llm_tools")
        self.assertIsNone(result.state.result.brief.goal)
        self.assertIsNone(result.state.result.brief.weight_kg)
        self.assertIsNone(result.state.result.brief.meals_per_day)
        self.assertIsNone(result.state.result.brief.pending_field)

    def test_deterministic_engine_is_physically_isolated_from_llm_chat_module(self):
        self.assertEqual(
            DeterministicNutritionIntakeChatEngine.__module__,
            "notas.application.ai_intake.deterministic_chat_engine",
        )
