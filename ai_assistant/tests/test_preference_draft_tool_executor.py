from django.test import SimpleTestCase

from ai_assistant.application.tools import (
    TOOL_UPDATE_PREFERENCE_DRAFT,
    ProfileDraftToolExecutor,
    execute_profile_draft_tool,
)
from ai_assistant.domain.contracts import AssistantToolRequest, AssistantToolStatus
from notas.application.ai_tools.results import tool_success


class PreferenceDraftToolExecutorTests(SimpleTestCase):
    def test_executes_preference_draft_tool_without_persistent_writes(self):
        calls = []

        def update_preference_draft(user, *, updates, current_draft=None, field_sources=None):
            calls.append((user, updates, current_draft, field_sources))
            return tool_success({"preference_draft": {"preferred_foods": updates["preferred_foods"]}})

        executor = ProfileDraftToolExecutor(dispatch_table={TOOL_UPDATE_PREFERENCE_DRAFT: update_preference_draft})

        result = executor.execute(
            AssistantToolRequest(
                tool_name=TOOL_UPDATE_PREFERENCE_DRAFT,
                arguments={"updates": {"preferred_foods": ["pollo", "arroz"]}},
                request_id="preference_draft_1",
            ),
            user="user-1",
        )

        self.assertEqual(result.status, AssistantToolStatus.OK)
        self.assertEqual(result.data["preference_draft"], {"preferred_foods": ["pollo", "arroz"]})
        self.assertEqual(calls, [("user-1", {"preferred_foods": ["pollo", "arroz"]}, None, None)])
        self.assertEqual(result.metadata["executor"], "profile_draft_tool_executor.v1")
        self.assertFalse(result.metadata["writes_allowed"])
        self.assertFalse(result.metadata["persistent_profile_updated"])
        self.assertTrue(result.metadata["draft_only"])
        self.assertTrue(result.metadata["requires_user_approval_for_persistence"])

    def test_convenience_executor_runs_preference_draft_tool(self):
        def update_preference_draft(user, *, updates, current_draft=None, field_sources=None):
            return tool_success({"preference_draft": {"avoided_foods": updates["avoided_foods"]}})

        result = execute_profile_draft_tool(
            AssistantToolRequest(
                tool_name=TOOL_UPDATE_PREFERENCE_DRAFT,
                arguments={"updates": {"avoided_foods": ["atun"]}},
            ),
            user="user-1",
            executor=ProfileDraftToolExecutor(dispatch_table={TOOL_UPDATE_PREFERENCE_DRAFT: update_preference_draft}),
        )

        self.assertEqual(result.status, AssistantToolStatus.OK)
        self.assertEqual(result.data["preference_draft"], {"avoided_foods": ["atun"]})
