from django.test import SimpleTestCase

from notas.application.ai_intake.chat_engine import _append_profile_draft_cards_from_llm_tools
from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    NutritionConversationMessage,
    NutritionConversationState,
    build_intake_result_from_brief,
)


class AiIntakeLLMProfileCardToolResultTests(SimpleTestCase):
    def _conversation(self):
        brief = NutritionBrief(raw_prompt="quiero una dieta", goal="muscle_gain")
        return NutritionConversationState(
            messages=[
                NutritionConversationMessage(role="user", text="mido 188"),
                NutritionConversationMessage(role="assistant", text="Perfecto, dejé la ficha actualizada para esta conversación."),
            ],
            result=build_intake_result_from_brief(brief),
        )

    def _metadata(self):
        return {
            "tool_results": [
                {
                    "tool_name": "share_profile_draft_card",
                    "status": "ok",
                    "data": {
                        "profile_draft_card": {
                            "title": "Ficha para esta propuesta",
                            "subtitle": "Datos personales usados en esta conversación.",
                            "items": [
                                {
                                    "key": "height_cm",
                                    "label": "Altura",
                                    "value": "188 cm",
                                    "is_pending": False,
                                    "source": "chat_draft",
                                    "source_label": "Este chat",
                                }
                            ],
                            "pending_count": 0,
                            "has_chat_draft_updates": True,
                            "can_update_personal_profile": True,
                            "status": "complete",
                        }
                    },
                    "metadata": {"executor": "profile_draft_tool_executor.v1"},
                }
            ]
        }

    def test_appends_profile_draft_card_from_llm_tool_result(self):
        conversation, count = _append_profile_draft_cards_from_llm_tools(
            self._conversation(),
            self._metadata(),
        )

        self.assertEqual(count, 1)
        self.assertEqual(conversation.messages[-1].role, "assistant")
        self.assertEqual(conversation.messages[-1].text, "")
        self.assertEqual(conversation.messages[-1].profile_draft_card["title"], "Ficha para esta propuesta")
        self.assertEqual(conversation.messages[-1].profile_draft_card["items"][0]["value"], "188 cm")

    def test_does_not_duplicate_same_profile_draft_card(self):
        conversation, count = _append_profile_draft_cards_from_llm_tools(
            self._conversation(),
            self._metadata(),
        )
        conversation, second_count = _append_profile_draft_cards_from_llm_tools(
            conversation,
            self._metadata(),
        )

        self.assertEqual(count, 1)
        self.assertEqual(second_count, 0)
        self.assertEqual(
            len([message for message in conversation.messages if message.profile_draft_card]),
            1,
        )

    def test_ignores_card_payload_attached_to_silent_update_tool(self):
        metadata = self._metadata()
        metadata["tool_results"][0]["tool_name"] = "update_profile_draft"

        conversation, count = _append_profile_draft_cards_from_llm_tools(
            self._conversation(),
            metadata,
        )

        self.assertEqual(count, 0)
        self.assertFalse(any(message.profile_draft_card for message in conversation.messages))
