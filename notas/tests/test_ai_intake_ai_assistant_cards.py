from types import SimpleNamespace

from django.test import SimpleTestCase

from ai_assistant.domain import (
    AssistantIntent,
    AssistantIntentName,
    AssistantMessage,
    AssistantMessageRole,
    AssistantStructuredResponse,
)
from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    NutritionConversationMessage,
    NutritionConversationState,
    build_intake_result_from_brief,
    serialize_conversation,
)
from notas.presentation.pages.ai_intake_page import (
    append_ai_assistant_structured_response,
    append_generated_plan_message,
    build_generated_plan_cards_for_ai_response,
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


def _proposal(proposal_id, *, title="Plan IA"):
    return SimpleNamespace(
        id=proposal_id,
        title=title,
        summary="Propuesta generada por My Scoope desde AI Assistant.",
        targets={"total_kcal": 2200, "protein": 160, "carbs": 240, "fat": 70},
        current_snapshot={},
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


def _structured_response(*, proposal_ids=()):
    return AssistantStructuredResponse(
        assistant_message=AssistantMessage(
            role=AssistantMessageRole.ASSISTANT,
            content="Listo. My Scoope generó una propuesta revisable.",
        ),
        intent=AssistantIntent(name=AssistantIntentName.CREATE_DAILYPLAN_PROPOSAL, confidence=0.9),
        proposal_ids=proposal_ids,
        requires_human_review=True,
        metadata={"tools_executed": True},
    )


class AiIntakeAiAssistantProposalCardTests(SimpleTestCase):
    def test_builds_cards_only_for_visible_proposals_matching_structured_response_ids(self):
        cards = build_generated_plan_cards_for_ai_response(
            structured_response=_structured_response(proposal_ids=[10, 99]),
            visible_proposals=[_proposal(10, title="Propuesta visible"), _proposal(11, title="Otra propuesta")],
        )

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].title, "Propuesta visible")
        self.assertEqual(cards[0].url, "/app/proposals/10/")

    def test_does_not_render_provider_or_unknown_proposal_ids_without_visible_objects(self):
        cards = build_generated_plan_cards_for_ai_response(
            structured_response=_structured_response(proposal_ids=[999]),
            visible_proposals=[],
        )

        self.assertEqual(cards, [])

    def test_appends_ai_assistant_text_and_current_proposal_card_to_conversation(self):
        conversation = append_ai_assistant_structured_response(
            _conversation(),
            structured_response=_structured_response(proposal_ids=[20]),
            visible_proposals=[_proposal(20, title="Plan generado por AI Assistant")],
        )

        payload = serialize_conversation(conversation)
        card_messages = [message for message in payload["messages"] if message.get("generated_plan_card")]

        self.assertEqual(conversation.messages[-2].text, "Listo. My Scoope generó una propuesta revisable.")
        self.assertEqual(len(card_messages), 1)
        self.assertEqual(card_messages[0]["generated_plan_card"]["title"], "Plan generado por AI Assistant")
        self.assertTrue(card_messages[0]["generated_plan_card"]["is_current"])

    def test_new_ai_assistant_card_deactivates_previous_chat_cards(self):
        conversation = append_generated_plan_message(
            _conversation(),
            proposal=_proposal(30, title="Propuesta anterior"),
        )

        conversation = append_ai_assistant_structured_response(
            conversation,
            structured_response=_structured_response(proposal_ids=[31]),
            visible_proposals=[_proposal(31, title="Propuesta nueva")],
        )

        cards = [message.generated_plan_card for message in conversation.messages if message.generated_plan_card]

        self.assertEqual(len(cards), 2)
        self.assertFalse(cards[0]["is_current"])
        self.assertTrue(cards[1]["is_current"])
