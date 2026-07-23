from django.test import SimpleTestCase

from ai_assistant.application.orchestrator import (
    AssistantOrchestratorConfig,
    ExternalLLMOrchestrator,
)
from ai_assistant.domain import (
    AssistantMessage,
    AssistantMessageRole,
    AssistantTurnRequest,
)
from ai_assistant.infrastructure.providers import FakeLLMClient


class SameFoodCalorieAssistantFlowTests(SimpleTestCase):
    def test_exact_user_request_exposes_resolution_and_safe_adjustment_tools(self):
        request = AssistantTurnRequest(
            user_message=AssistantMessage(
                role=AssistantMessageRole.USER,
                content=(
                    "Cambia a mi plan X la cantidad de calorías, auméntalas en "
                    "200 calorías manteniendo los mismos alimentos pero variando cantidades."
                ),
            ),
            context={"surface": "ai_nutrition_intake"},
        )
        provider_request = ExternalLLMOrchestrator(
            llm_client=FakeLLMClient(),
            config=AssistantOrchestratorConfig(
                enable_reviewable_proposal_tools=True,
            ),
        ).build_provider_request(request)
        tool_names = {
            str(tool.get("name") or "")
            for tool in provider_request.tools
        }

        self.assertIn("search_user_dailyplans", tool_names)
        self.assertIn("read_dailyplan", tool_names)
        self.assertIn(
            "create_proportional_dailyplan_calorie_proposal",
            tool_names,
        )
        self.assertNotIn("read_account_billing_context", tool_names)
