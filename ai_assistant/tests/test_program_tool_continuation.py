import json

from django.test import SimpleTestCase

from ai_assistant.application.limits import estimate_provider_request_tokens
from ai_assistant.application.orchestrator import AssistantOrchestratorConfig, ExternalLLMOrchestrator
from ai_assistant.application.tools import (
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS as CREATE,
)
from ai_assistant.application.tools import (
    TOOL_UPDATE_PROPOSAL_PREFERENCES as UPDATE,
)
from ai_assistant.domain import AssistantMessage, AssistantToolResult, AssistantTurnRequest
from ai_assistant.infrastructure.providers import FakeLLMClient


class ProgramToolContinuationTests(SimpleTestCase):
    def setUp(self):
        self.orchestrator = ExternalLLMOrchestrator(
            llm_client=FakeLLMClient(),
            config=AssistantOrchestratorConfig(enable_reviewable_proposal_tools=True, max_input_tokens=6000),
        )
        self.request = AssistantTurnRequest(
            user_message=AssistantMessage(role="user", content=(
                "Crea un programa de 8 semanas, 2400 kcal diarias. Indica cuántos menús distintos tiene."
            )),
            context={"surface": "ai_nutrition_intake", "metadata": {"tool_oriented_intake": {
                "work_progress": {"active_objective": "create_reviewable_program_proposal", "blocking_fields": ["goal"],
                    "active_work": {"resource": "program", "expected_outcome": "nutrition_proposal"}},
            }}},
        )
        self.captured = AssistantToolResult(tool_name=UPDATE, status="ok", request_id="capture", data={
            "proposal_preferences": {"requested_entity": "program", "duration_weeks": 8,
                "calorie_target": 2400, "meals_per_day": 4,
                "macro_distribution": {"protein": 30, "carbs": 50, "fat": 20}},
        })

    def followup(self, results, *, remaining=3, continuation=()):
        return self.orchestrator.build_tool_followup_provider_request(
            request=self.request, continuation_items=continuation, tool_results=results[-1:],
            accumulated_tool_results=results, remaining_tool_iterations=remaining,
        )

    def test_menu_count_request_does_not_replace_creation_with_library_query(self):
        initial = self.orchestrator.build_provider_request(self.request)
        self.assertNotIn("query_workspace", {tool["name"] for tool in initial.tools})
        self.assertEqual(initial.tool_choice, {"type": "function", "name": UPDATE})

    def test_large_history_keeps_pending_program_creation_and_complete_draft(self):
        followup = self.followup((self.captured,), continuation=({"type": "message", "content": "history " * 8000},))
        self.assertEqual(followup.tool_choice, {"type": "function", "name": CREATE})
        self.assertEqual([tool["name"] for tool in followup.tools], [CREATE])
        self.assertLessEqual(estimate_provider_request_tokens(followup), 6000)
        self.assertEqual(followup.continuation_items, ())
        self.assertEqual(followup.tool_outputs, ())
        self.assertEqual(json.loads(followup.messages[-1].content)["latest_typed_drafts"]["proposal_preferences"],
                         self.captured.data["proposal_preferences"])
        self.assertIn(self.request.user_message.content, [m.content for m in followup.messages])

    def test_successful_program_is_not_created_again(self):
        created = AssistantToolResult(tool_name=CREATE, status="ok", request_id="created",
                                      data={"proposal": {"id": 123, "status": "pending_review"}})
        followup = self.followup((self.captured, created))
        self.assertEqual(followup.tools, ())
        self.assertIsNone(followup.tool_choice)

    def test_compaction_does_not_extend_exhausted_iteration_budget(self):
        followup = self.followup((self.captured,), remaining=0)
        self.assertEqual(followup.tools, ())
        self.assertIsNone(followup.tool_choice)
