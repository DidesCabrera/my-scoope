from types import SimpleNamespace

from django.test import SimpleTestCase

from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    NutritionConversationMessage,
    NutritionConversationState,
    build_intake_result_from_brief,
    deserialize_conversation,
    serialize_conversation,
)
from notas.presentation.pages.ai_intake_page import (
    append_generated_plan_message,
    append_iterated_plan_message,
)


def _conversation():
    brief = NutritionBrief(
        raw_prompt="quiero bajar grasa, 4 comidas, simple",
        goal="fat_loss",
        meals_per_day=4,
        style_preferences=["simple"],
        weight_kg=80,
        height_cm=178,
        age_years=30,
        sex="male",
        activity_level="moderate",
    )
    return NutritionConversationState(
        messages=[
            NutritionConversationMessage(role="user", text="quiero bajar grasa"),
            NutritionConversationMessage(role="assistant", text="Ya tengo suficiente."),
        ],
        result=build_intake_result_from_brief(brief),
    )


def _proposal(proposal_id, *, title="Plan IA", iteration=None):
    return SimpleNamespace(
        id=proposal_id,
        title=title,
        summary="Propuesta generada desde chat.",
        targets={"total_kcal": 2200, "protein": 160, "carbs": 240, "fat": 70},
        current_snapshot={"iteration": iteration} if iteration else {},
        validation_summary={},
        proposed_payload={
            "intent": "create_dailyplan",
            "dailyplan": {
                "name": title,
                "meals": [
                    {"hour": "08:00", "meal": {"name": "Desayuno", "foods": [{"name": "Avena"}]}},
                    {"hour": "13:00", "meal": {"name": "Almuerzo", "foods": [{"name": "Pollo"}]}},
                ],
            },
        },
    )


class AiIntakeGeneratedPlanCardTests(SimpleTestCase):
    def test_generated_plan_card_is_serialized_in_conversation_message(self):
        conversation = append_generated_plan_message(
            _conversation(),
            proposal=_proposal(10, title="Propuesta v1"),
        )

        payload = serialize_conversation(conversation)
        card_messages = [message for message in payload["messages"] if message.get("generated_plan_card")]

        self.assertEqual(len(card_messages), 1)
        self.assertEqual(card_messages[0]["generated_plan_card"]["title"], "Propuesta v1")
        self.assertTrue(card_messages[0]["generated_plan_card"]["is_current"])

    def test_deserialize_conversation_preserves_generated_plan_cards(self):
        conversation = append_generated_plan_message(
            _conversation(),
            proposal=_proposal(11, title="Propuesta v1"),
        )

        restored = deserialize_conversation(serialize_conversation(conversation))

        self.assertIsNotNone(restored)
        self.assertTrue(any(message.generated_plan_card for message in restored.messages))

    def test_iterated_plan_keeps_previous_card_and_marks_new_card_current(self):
        conversation = append_generated_plan_message(
            _conversation(),
            proposal=_proposal(12, title="Propuesta v1"),
        )

        iterated = append_iterated_plan_message(
            conversation,
            user_message="sin arroz",
            previous_proposal=_proposal(12, title="Propuesta v1"),
            proposal=_proposal(13, title="Propuesta v2"),
        )

        cards = [message.generated_plan_card for message in iterated.messages if message.generated_plan_card]

        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["title"], "Propuesta v1")
        self.assertFalse(cards[0]["is_current"])
        self.assertEqual(cards[1]["title"], "Propuesta v2")
        self.assertTrue(cards[1]["is_current"])

    def test_iterated_plan_adds_legacy_previous_card_when_chat_has_no_card_snapshot(self):
        iterated = append_iterated_plan_message(
            _conversation(),
            user_message="menos comidas",
            previous_proposal=_proposal(14, title="Propuesta anterior"),
            proposal=_proposal(15, title="Propuesta nueva"),
        )

        cards = [message.generated_plan_card for message in iterated.messages if message.generated_plan_card]

        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["title"], "Propuesta anterior")
        self.assertFalse(cards[0]["is_current"])
        self.assertEqual(cards[1]["title"], "Propuesta nueva")
        self.assertTrue(cards[1]["is_current"])

    def test_iterated_plan_card_exposes_iteration_trace(self):
        iteration = {
            "previous_proposal_id": 20,
            "user_message": "sin arroz y más proteína",
            "command_labels": ["Evitar arroz", "Subir proteína objetivo"],
            "command_set": {
                "commands": [
                    {"kind": "avoid_food", "value": "arroz"},
                    {"kind": "adjust_target", "metric": "protein", "direction": "increase"},
                ],
            },
        }
        conversation = append_generated_plan_message(
            _conversation(),
            proposal=_proposal(21, title="Propuesta v2", iteration=iteration),
        )

        cards = [message.generated_plan_card for message in conversation.messages if message.generated_plan_card]

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["iteration_trace"]["previous_proposal_id"], 20)
        self.assertEqual(cards[0]["iteration_trace"]["command_count"], 2)
        self.assertEqual(cards[0]["iteration_trace"]["short_label"], "Evitar arroz · Subir proteína objetivo")
        self.assertEqual(cards[0]["previous_proposal_url"], "/app/proposals/20/")
