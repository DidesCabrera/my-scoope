from django.test import SimpleTestCase

from ai_assistant.application.objective_state import infer_active_work
from ai_assistant.application.personal_record_intent import parse_personal_record_request
from ai_assistant.application.tool_selection import (
    initial_tool_choice,
    next_personal_record_read_tool,
    select_provider_tools,
)
from ai_assistant.application.tools import (
    TOOL_READ_USER_PREFERENCE_CONTEXT,
    TOOL_READ_USER_PROFILE_CONTEXT,
    list_provider_tool_specs,
)
from ai_assistant.domain import AssistantMessage, AssistantTurnRequest


class PersonalRecordIntentTests(SimpleTestCase):
    def _selected(self, message: str) -> set[str]:
        request = AssistantTurnRequest(
            user_message=AssistantMessage(role="user", content=message),
            context={"surface": "ai_nutrition_intake"},
        )
        return {
            item["name"]
            for item in select_provider_tools(
                request,
                available=list_provider_tool_specs(),
                enable_reviewable_proposal_tools=True,
            )
        }

    def test_recognizes_each_registered_personal_record_name(self):
        cases = {
            "Muéstrame mi ficha corporal": ("body",),
            "Enséñame objetivo y actividad": ("planning",),
            "Quiero ver mis preferencias alimentarias": ("preferences",),
            "Muéstrame mis métricas corporales": ("metrics",),
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                request = parse_personal_record_request(message)
                self.assertIsNotNone(request)
                self.assertEqual(request.kinds, expected)
                self.assertFalse(request.ambiguous)

    def test_plural_personal_records_requests_all_registered_cards(self):
        request = parse_personal_record_request("Muéstrame todas mis fichas personales")

        self.assertEqual(request.kinds, ("body", "planning", "preferences", "metrics"))
        selected = self._selected("Muéstrame todas mis fichas personales")
        self.assertIn(TOOL_READ_USER_PROFILE_CONTEXT, selected)
        self.assertIn(TOOL_READ_USER_PREFERENCE_CONTEXT, selected)

        turn = AssistantTurnRequest(
            user_message=AssistantMessage(role="user", content="Muéstrame todas mis fichas personales"),
            context={"surface": "ai_nutrition_intake"},
        )
        tools = [tool for tool in list_provider_tool_specs() if tool["name"] in selected]
        self.assertEqual(initial_tool_choice(turn, tools), {"type": "function", "name": TOOL_READ_USER_PROFILE_CONTEXT})
        completed_profile = type("Result", (), {"ok": True, "tool_name": TOOL_READ_USER_PROFILE_CONTEXT})()
        self.assertEqual(next_personal_record_read_tool(turn, (completed_profile,)), TOOL_READ_USER_PREFERENCE_CONTEXT)

    def test_each_record_selects_only_its_persisted_source(self):
        body = self._selected("Muéstrame mi ficha corporal")
        preferences = self._selected("Muéstrame mis preferencias alimentarias")
        self.assertIn(TOOL_READ_USER_PROFILE_CONTEXT, body)
        self.assertNotIn(TOOL_READ_USER_PREFERENCE_CONTEXT, body)
        self.assertIn(TOOL_READ_USER_PREFERENCE_CONTEXT, preferences)
        self.assertNotIn(TOOL_READ_USER_PROFILE_CONTEXT, preferences)

    def test_generic_singular_ficha_requires_clarification_without_memory_tools(self):
        message = "Muéstrame mi ficha personal"
        request = parse_personal_record_request(message)

        self.assertTrue(request.ambiguous)
        self.assertNotIn(TOOL_READ_USER_PROFILE_CONTEXT, self._selected(message))
        self.assertNotIn(TOOL_READ_USER_PREFERENCE_CONTEXT, self._selected(message))
        active = infer_active_work(None, current_user_message=message)
        self.assertEqual(active["expected_outcome"], "clarification_required")
        self.assertEqual(active["action"], "clarify")
        self.assertEqual(len(active["clarification_options"]), 5)
