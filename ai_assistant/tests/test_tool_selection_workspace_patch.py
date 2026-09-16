from django.test import SimpleTestCase

from ai_assistant.application.tool_selection import select_provider_tools
from ai_assistant.application.tools import (
    TOOL_PREPARE_PRODUCT_ACTION,
    TOOL_PROPOSE_WORKSPACE_PATCH,
    list_provider_tool_specs,
)
from ai_assistant.domain import AssistantMessage, AssistantTurnRequest


class WorkspacePatchToolSelectionTests(SimpleTestCase):
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
