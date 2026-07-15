from django.test import SimpleTestCase

from ai_assistant.application.tools import (
    ProfileDraftToolExecutor,
    TOOL_UPDATE_PROPOSAL_PREFERENCES,
    execute_profile_draft_tool,
)
from ai_assistant.domain.contracts import AssistantToolRequest, AssistantToolStatus
from notas.application.ai_tools.results import tool_success


class ProposalPreferenceDraftToolExecutorTests(SimpleTestCase):
    def test_executes_proposal_preference_tool_without_persistent_writes(self):
        calls = []

        def update_proposal_preferences(user, *, updates, current_preferences=None, field_sources=None):
            calls.append((user, updates, current_preferences, field_sources))
            return tool_success({"proposal_preferences": {"goal": updates["goal"]}})

        executor = ProfileDraftToolExecutor(
            dispatch_table={TOOL_UPDATE_PROPOSAL_PREFERENCES: update_proposal_preferences}
        )

        result = executor.execute(
            AssistantToolRequest(
                tool_name=TOOL_UPDATE_PROPOSAL_PREFERENCES,
                arguments={"updates": {"goal": "muscle_gain"}},
                request_id="proposal_preferences_1",
            ),
            user="user-1",
        )

        self.assertEqual(result.status, AssistantToolStatus.OK)
        self.assertEqual(result.data["proposal_preferences"], {"goal": "muscle_gain"})
        self.assertEqual(calls, [("user-1", {"goal": "muscle_gain"}, None, None)])
        self.assertEqual(result.metadata["executor"], "profile_draft_tool_executor.v1")
        self.assertFalse(result.metadata["writes_allowed"])
        self.assertTrue(result.metadata["draft_only"])

    def test_convenience_executor_runs_proposal_preference_tool(self):
        def update_proposal_preferences(user, *, updates, current_preferences=None, field_sources=None):
            return tool_success({"proposal_preferences": {"meals_per_day": updates["meals_per_day"]}})

        result = execute_profile_draft_tool(
            AssistantToolRequest(
                tool_name=TOOL_UPDATE_PROPOSAL_PREFERENCES,
                arguments={"updates": {"meals_per_day": 4}},
            ),
            user="user-1",
            executor=ProfileDraftToolExecutor(
                dispatch_table={TOOL_UPDATE_PROPOSAL_PREFERENCES: update_proposal_preferences}
            ),
        )

        self.assertEqual(result.status, AssistantToolStatus.OK)
        self.assertEqual(result.data["proposal_preferences"], {"meals_per_day": 4})
