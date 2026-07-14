from django.test import SimpleTestCase

from ai_assistant.application.chat_engines import ChatEngineRequest, ChatEngineTurnResult
from notas.application.ai_intake.chat_engine import (
    AI_ASSISTANT_CHAT_ENGINE_LLM_PREVIEW,
    LLMPreviewNutritionIntakeChatEngine,
    _apply_llm_tool_results_to_conversation_state,
    _append_draft_cards_from_llm_tools,
)
from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    NutritionConversationMessage,
    NutritionConversationState,
    append_profile_update_confirmation_message,
    build_intake_result_from_brief,
    serialize_conversation,
    start_or_continue_conversation,
)


class _StubBaselineEngine:
    engine_name = "stub_baseline"

    def __init__(self, conversation):
        self.conversation = conversation

    def continue_chat(self, request):
        return ChatEngineTurnResult(
            state=self.conversation,
            assistant_text=self.conversation.last_assistant_message,
            is_ready_for_proposal=self.conversation.is_ready_for_proposal,
            engine_name=self.engine_name,
            metadata={"stub": True},
        )


class _StubLLMEngine:
    engine_name = "stub_llm"

    def __init__(self, *, assistant_text, metadata):
        self.assistant_text = assistant_text
        self.metadata = metadata
        self.requests = []

    def continue_chat(self, request):
        self.requests.append(request)
        return ChatEngineTurnResult(
            state=object(),
            assistant_text=self.assistant_text,
            is_ready_for_proposal=False,
            engine_name=self.engine_name,
            metadata=self.metadata,
        )


def _conversation(brief=None, assistant_text="Para orientarla bien, cuéntame cuál es tu objetivo principal ahora."):
    brief = brief or NutritionBrief(raw_prompt="quiero una dieta")
    return NutritionConversationState(
        messages=[
            NutritionConversationMessage(role="user", text="quiero una dieta"),
            NutritionConversationMessage(role="assistant", text=assistant_text),
        ],
        result=build_intake_result_from_brief(brief),
    )


class AiIntakeToolLedRegressionTests(SimpleTestCase):
    def test_tool_results_update_state_without_deterministic_visible_text_override(self):
        """Tool results update the brief, but LLM visible text is no longer overwritten by regex guards."""

        metadata = {
            "tools_executed": True,
            "tool_requests": 1,
            "tool_results": [
                {
                    "tool_name": "update_proposal_preferences",
                    "status": "ok",
                    "data": {
                        "proposal_preferences": {
                            "goal": "muscle_gain",
                            "field_sources": {"goal": "chat_draft"},
                        },
                        "nutrition_brief_patch": {"goal": "muscle_gain"},
                    },
                }
            ],
        }
        engine = LLMPreviewNutritionIntakeChatEngine(
            baseline_engine=_StubBaselineEngine(_conversation()),
            llm_engine=_StubLLMEngine(
                assistant_text="Perfecto. ¿Cuál es tu objetivo principal ahora: bajar grasa, ganar masa, mantener o rendimiento?",
                metadata=metadata,
            ),
        )

        result = engine.continue_chat(
            ChatEngineRequest(
                message="aumentar de musculo",
                metadata={"chat_engine_mode": AI_ASSISTANT_CHAT_ENGINE_LLM_PREVIEW},
            )
        )

        self.assertEqual(result.state.result.brief.goal, "muscle_gain")
        self.assertIn("objetivo principal", result.assistant_text.lower())
        self.assertFalse(result.metadata.get("llm_tool_state_visible_text_guarded", False))
        self.assertEqual(result.metadata.get("llm_preview_fallback_reason", ""), "")
        self.assertTrue(result.metadata["deterministic_coauthor_disabled"])

    def test_tool_results_can_update_multiple_memory_objects_in_one_turn(self):
        conversation = _conversation(NutritionBrief(raw_prompt="quiero una dieta"))
        metadata = {
            "tool_results": [
                {
                    "tool_name": "update_profile_draft",
                    "status": "ok",
                    "data": {
                        "profile_draft": {
                            "age_years": 38,
                            "height_cm": 188,
                            "weight_kg": 85,
                            "sex": "male",
                            "activity_level": "high",
                            "training_frequency": 3,
                            "field_sources": {
                                "age_years": "chat_draft",
                                "height_cm": "chat_draft",
                                "weight_kg": "chat_draft",
                                "sex": "chat_draft",
                                "activity_level": "chat_draft",
                                "training_frequency": "chat_draft",
                            },
                        },
                        "profile_draft_card": {
                            "title": "Ficha para esta propuesta",
                            "subtitle": "Datos personales usados en esta conversación.",
                            "items": [
                                {"key": "weight_kg", "label": "Peso", "value": "85 kg", "is_pending": False, "source": "chat_draft", "source_label": "Este chat"},
                                {"key": "height_cm", "label": "Altura", "value": "188 cm", "is_pending": False, "source": "chat_draft", "source_label": "Este chat"},
                            ],
                            "pending_count": 0,
                            "status": "complete",
                            "has_chat_draft_updates": True,
                            "can_update_personal_profile": True,
                        },
                    },
                },
                {
                    "tool_name": "update_preference_draft",
                    "status": "ok",
                    "data": {
                        "preference_draft": {
                            "avoided_foods": ["atun"],
                            "preferred_foods": ["pollo", "huevos"],
                            "simplicity_preference": "high",
                        },
                        "preference_draft_card": {
                            "title": "Preferencias para esta propuesta",
                            "sections": [
                                {
                                    "title": "Preferencias alimentarias",
                                    "items": [
                                        {"key": "avoided_foods", "label": "Alimentos evitados", "value": "atun", "is_pending": False, "source": "chat_draft", "source_label": "Este chat"},
                                    ],
                                }
                            ],
                            "known_count": 1,
                            "status": "has_data",
                        },
                    },
                },
                {
                    "tool_name": "update_proposal_preferences",
                    "status": "ok",
                    "data": {
                        "proposal_preferences": {
                            "goal": "muscle_gain",
                            "meals_per_day": 3,
                            "energy_adjustment": "surplus_mild",
                        },
                        "proposal_preferences_card": {
                            "title": "Preferencias de propuesta",
                            "sections": [
                                {
                                    "title": "Dirección de la propuesta",
                                    "items": [
                                        {"key": "goal", "label": "Objetivo", "value": "Ganar masa muscular", "is_pending": False, "source": "chat_draft", "source_label": "Este chat"},
                                    ],
                                }
                            ],
                            "known_count": 1,
                            "status": "has_data",
                        },
                    },
                },
            ]
        }

        synced, applied = _apply_llm_tool_results_to_conversation_state(conversation, metadata)
        with_cards, profile_cards, preference_cards, proposal_cards = _append_draft_cards_from_llm_tools(synced, metadata)
        brief = with_cards.result.brief

        self.assertEqual(applied, 3)
        self.assertEqual(brief.goal, "muscle_gain")
        self.assertEqual(brief.age_years, 38)
        self.assertEqual(brief.height_cm, 188)
        self.assertEqual(brief.weight_kg, 85)
        self.assertEqual(brief.sex, "male")
        self.assertEqual(brief.activity_level, "high")
        self.assertEqual(brief.training_frequency, 3)
        self.assertEqual(brief.meals_per_day, 3)
        self.assertEqual(brief.energy_adjustment, "surplus_mild")
        self.assertEqual(brief.excluded_foods, ["atun"])
        self.assertEqual(brief.preferred_foods, ["pollo", "huevos"])
        self.assertIn("simple", brief.style_preferences)
        self.assertEqual((profile_cards, preference_cards, proposal_cards), (0, 0, 0))
        self.assertFalse(any(m.profile_draft_card for m in with_cards.messages))
        self.assertFalse(any(m.preference_draft_card for m in with_cards.messages))
        self.assertFalse(any(m.proposal_preferences_card for m in with_cards.messages))

    def test_approval_boundary_remains_outside_llm_draft_tool_results(self):
        conversation = _conversation(NutritionBrief(raw_prompt="quiero una dieta"))
        metadata = {
            "tool_results": [
                {
                    "tool_name": "update_profile_draft",
                    "status": "ok",
                    "data": {
                        "profile_draft": {
                            "height_cm": 188,
                            "field_sources": {"height_cm": "chat_draft"},
                        },
                        "source_boundary": {
                            "persistent_profile_updated": False,
                            "persistence_requires_user_approval": True,
                        },
                    },
                    "metadata": {"writes_allowed": False},
                }
            ]
        }

        updated, applied = _apply_llm_tool_results_to_conversation_state(conversation, metadata)

        self.assertEqual(applied, 1)
        self.assertEqual(updated.result.brief.height_cm, 188)
        self.assertEqual(updated.result.brief.field_sources["height_cm"], "chat_draft")
        self.assertFalse(metadata["tool_results"][0]["metadata"]["writes_allowed"])
        self.assertFalse(metadata["tool_results"][0]["data"]["source_boundary"]["persistent_profile_updated"])

    def test_contextual_meals_answer_accepts_veces_al_dia_when_meals_are_pending(self):
        state = start_or_continue_conversation(message="quiero una dieta")
        for message in (
            "ganar masa",
            "usar mi ficha",
            "85 kg",
            "188",
            "38",
            "hombre",
            "entreno 3 veces por semana",
        ):
            state = start_or_continue_conversation(
                message=message,
                existing_payload=serialize_conversation(state),
            )

        self.assertEqual(state.result.brief.pending_field, "meals_per_day")

        state = start_or_continue_conversation(
            message="3 veces al día",
            existing_payload=serialize_conversation(state),
        )

        self.assertEqual(state.result.brief.meals_per_day, 3)
        self.assertNotEqual(state.result.brief.pending_field, "meals_per_day")

    def test_profile_update_confirmation_deactivates_previous_actionable_cards(self):
        brief = NutritionBrief(
            raw_prompt="quiero una dieta",
            subject_source="self_profile",
            goal="muscle_gain",
            weight_kg=84,
            height_cm=188,
            age_years=38,
            sex="male",
            activity_level="moderate",
            field_sources={
                "weight_kg": "profile",
                "height_cm": "chat_draft",
                "age_years": "chat_draft",
                "sex": "chat_draft",
                "activity_level": "chat_draft",
            },
        )
        conversation = NutritionConversationState(
            messages=[
                NutritionConversationMessage(
                    role="assistant",
                    text="",
                    profile_draft_card={
                        "title": "Ficha para esta propuesta",
                        "subtitle": "Datos personales usados en esta conversación.",
                        "items": [],
                        "pending_count": 0,
                        "has_chat_draft_updates": True,
                        "can_update_personal_profile": True,
                        "status": "complete",
                    },
                )
            ],
            result=build_intake_result_from_brief(brief),
        )
        updated_brief = NutritionBrief(
            raw_prompt=brief.raw_prompt,
            subject_source=brief.subject_source,
            goal=brief.goal,
            weight_kg=brief.weight_kg,
            height_cm=brief.height_cm,
            age_years=brief.age_years,
            sex=brief.sex,
            activity_level=brief.activity_level,
            field_sources={
                "weight_kg": "profile",
                "height_cm": "profile",
                "age_years": "chat_draft",
                "sex": "profile",
                "activity_level": "chat_draft",
            },
        )

        updated = append_profile_update_confirmation_message(
            conversation,
            brief=updated_brief,
            assistant_text="Listo, actualicé la altura en tu ficha personal.",
        )

        cards = [message.profile_draft_card for message in updated.messages if message.profile_draft_card]
        self.assertGreaterEqual(len(cards), 2)
        self.assertFalse(cards[0]["can_update_personal_profile"])
        self.assertTrue(cards[0]["profile_update_action_consumed"])
        self.assertFalse(cards[-1]["can_update_personal_profile"])
