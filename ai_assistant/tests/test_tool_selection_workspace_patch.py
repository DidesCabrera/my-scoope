from django.test import SimpleTestCase

from ai_assistant.application.tool_selection import initial_tool_choice, select_provider_tools
from ai_assistant.application.tools import (
    TOOL_PREPARE_PRODUCT_ACTION,
    TOOL_PROPOSE_WORKSPACE_PATCH,
    TOOL_QUERY_WORKSPACE,
    TOOL_READ_USER_PREFERENCE_CONTEXT,
    TOOL_READ_USER_PROFILE_CONTEXT,
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

        self.assertIn(TOOL_QUERY_WORKSPACE, names)
        self.assertNotIn("list_user_programs", names)
        self.assertNotIn("read_calendarization", names)
        self.assertEqual(initial_tool_choice(request, selected), "required")

    def test_intake_library_plan_request_exposes_plan_list_and_requires_evidence(self):
        request, selected, names = self._selected_for_intake(
            "¿Puedes decirme los planes que existen en mi librería?"
        )

        self.assertIn(TOOL_QUERY_WORKSPACE, names)
        self.assertNotIn("list_user_dailyplans", names)
        self.assertEqual(initial_tool_choice(request, selected), "required")

    def test_intake_accentless_library_program_request_requires_program_listing(self):
        request, selected, names = self._selected_for_intake(
            "gracias, y puedes listarme los programas que tengo en mi libreria?"
        )

        self.assertIn(TOOL_QUERY_WORKSPACE, names)
        self.assertNotIn("list_user_programs", names)
        self.assertEqual(initial_tool_choice(request, selected), "required")

    def test_intake_library_reads_remain_discoverable_without_phrase_matching(self):
        request, selected, names = self._selected_for_intake(
            "¿Cuáles son mis programas?"
        )

        self.assertIn(TOOL_QUERY_WORKSPACE, names)
        self.assertNotIn("list_user_programs", names)
        self.assertNotIn("list_user_dailyplans", names)
        self.assertEqual(initial_tool_choice(request, selected), "auto")

    def test_intake_indirect_memory_and_reviewed_change_request_exposes_capabilities(self):
        request, selected, names = self._selected_for_intake(
            "Ten en cuenta lo que ya sabes de mí y déjalo mejor organizado."
        )

        self.assertIn(TOOL_READ_USER_PROFILE_CONTEXT, names)
        self.assertIn(TOOL_READ_USER_PREFERENCE_CONTEXT, names)
        self.assertIn(TOOL_PROPOSE_WORKSPACE_PATCH, names)
        self.assertLessEqual(len(selected), 12)

    def test_intake_food_and_meal_creation_exposes_workspace_patch(self):
        request, selected, names = self._selected_for_intake(
            "Creo que esos alimentos no están disponibles en el sistema, ¿podrías "
            "crearlos como alimentos en mi librería para dejarlos en una comida registrados?"
        )

        self.assertIn(TOOL_QUERY_WORKSPACE, names)
        self.assertNotIn("list_user_foods", names)
        self.assertNotIn("list_user_meals", names)
        self.assertIn(TOOL_PROPOSE_WORKSPACE_PATCH, names)
        self.assertEqual(initial_tool_choice(request, selected), "required")

    def test_short_acknowledgement_keeps_tools_from_prior_operational_request(self):
        request = AssistantTurnRequest(
            user_message=AssistantMessage(role="user", content="sí claro"),
            history=(
                AssistantMessage(role="user", content="Créame una comida de 450 kcal"),
                AssistantMessage(
                    role="assistant",
                    content="Puedo reintentarlo con objetivos de macros flexibles.",
                ),
            ),
            context={"surface": "ai_nutrition_intake"},
        )

        selected = select_provider_tools(
            request,
            available=list_provider_tool_specs(),
            enable_reviewable_proposal_tools=True,
        )
        names = {item["name"] for item in selected}

        self.assertIn(TOOL_QUERY_WORKSPACE, names)
        self.assertIn("create_nutrition_solver_meal_proposal", names)
        self.assertNotIn("create_nutrition_engine_dailyplan_proposal", names)
        self.assertEqual(initial_tool_choice(request, selected), "required")
