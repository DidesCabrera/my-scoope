from django.test import SimpleTestCase

from ai_assistant.application.tool_selection import initial_tool_choice, select_provider_tools
from ai_assistant.application.tools import (
    TOOL_PREPARE_PRODUCT_ACTION,
    TOOL_PROPOSE_WORKSPACE_PATCH,
    list_provider_tool_specs,
)
from ai_assistant.domain import AssistantMessage, AssistantTurnRequest


class WorkspacePatchToolSelectionTests(SimpleTestCase):
    def _selected_for_intake(self, message: str):
        request = AssistantTurnRequest(
            user_message=AssistantMessage(role="user", content=message),
            context={"surface": "ai_nutrition_intake"},
        )
        selected = select_provider_tools(
            request,
            available=list_provider_tool_specs(),
            enable_reviewable_proposal_tools=True,
        )
        return request, selected, {item["name"] for item in selected}

    def test_general_mutation_selects_workspace_patch_and_not_legacy_micro_tool(self):
        request = AssistantTurnRequest(
            user_message=AssistantMessage(
                role="user",
                content="Renombra mi comida y crea un plan nuevo.",
            )
        )

        selected = select_provider_tools(
            request,
            available=list_provider_tool_specs(),
            enable_reviewable_proposal_tools=True,
        )
        names = {item["name"] for item in selected}

        self.assertIn(TOOL_PROPOSE_WORKSPACE_PATCH, names)
        self.assertNotIn(TOOL_PREPARE_PRODUCT_ACTION, names)

    def test_nutrition_proposal_request_does_not_confuse_patch_with_proposal_creation(self):
        request = AssistantTurnRequest(
            user_message=AssistantMessage(
                role="user",
                content="Quiero una propuesta de comida alta en proteína.",
            )
        )

        selected = select_provider_tools(
            request,
            available=list_provider_tool_specs(),
            enable_reviewable_proposal_tools=True,
        )

        self.assertNotIn(TOOL_PROPOSE_WORKSPACE_PATCH, {item["name"] for item in selected})

    def test_intake_program_status_request_exposes_program_and_calendar_reads(self):
        request, selected, names = self._selected_for_intake(
            "Hola, ¿podrías decirme si tengo algún programa en curso?"
        )

        self.assertIn("list_user_programs", names)
        self.assertIn("read_calendarization", names)
        self.assertEqual(initial_tool_choice(request, selected), "required")

    def test_intake_library_plan_request_exposes_plan_list_and_requires_evidence(self):
        request, selected, names = self._selected_for_intake(
            "¿Puedes decirme los planes que existen en mi librería?"
        )

        self.assertIn("list_user_dailyplans", names)
        self.assertEqual(initial_tool_choice(request, selected), "required")

    def test_intake_food_and_meal_creation_exposes_workspace_patch(self):
        request, selected, names = self._selected_for_intake(
            "Creo que esos alimentos no están disponibles en el sistema, ¿podrías "
            "crearlos como alimentos en mi librería para dejarlos en una comida registrados?"
        )

        self.assertIn("list_user_foods", names)
        self.assertIn("list_user_meals", names)
        self.assertIn(TOOL_PROPOSE_WORKSPACE_PATCH, names)
        self.assertEqual(initial_tool_choice(request, selected), "required")
