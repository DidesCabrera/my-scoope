from django.test import SimpleTestCase

from ai_assistant.application.tools import (
    ProfileDraftToolExecutor,
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
    TOOL_UPDATE_PROFILE_DRAFT,
    execute_profile_draft_tool,
)
from ai_assistant.domain.contracts import AssistantToolRequest, AssistantToolStatus
from notas.application.ai_tools.results import tool_error, tool_success


class ProfileDraftToolExecutorTests(SimpleTestCase):
    def test_executes_profile_draft_tool_without_persistent_writes(self):
        calls = []

        def update_profile_draft(user, *, updates, current_draft=None, field_sources=None):
            calls.append((user, updates, current_draft, field_sources))
            return tool_success({"profile_draft": {"height_cm": updates["height_cm"]}})

        executor = ProfileDraftToolExecutor(dispatch_table={TOOL_UPDATE_PROFILE_DRAFT: update_profile_draft})

        result = executor.execute(
            AssistantToolRequest(
                tool_name=TOOL_UPDATE_PROFILE_DRAFT,
                arguments={"updates": {"height_cm": 188}},
                request_id="draft_1",
            ),
            user="user-1",
        )

        self.assertEqual(result.status, AssistantToolStatus.OK)
        self.assertEqual(result.data["profile_draft"], {"height_cm": 188})
        self.assertEqual(calls, [("user-1", {"height_cm": 188}, None, None)])
        self.assertEqual(result.metadata["executor"], "profile_draft_tool_executor.v1")
        self.assertFalse(result.metadata["writes_allowed"])
        self.assertFalse(result.metadata["persistent_profile_updated"])
        self.assertTrue(result.metadata["draft_only"])
        self.assertTrue(result.metadata["requires_user_approval_for_persistence"])

    def test_blocks_non_draft_tool(self):
        executor = ProfileDraftToolExecutor(
            dispatch_table={TOOL_COMPARE_DAILYPLAN_TO_TARGETS: lambda user, **kwargs: tool_success({})}
        )

        result = executor.execute(
            AssistantToolRequest(
                tool_name=TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
                arguments={"dailyplan_id": 1, "targets": {"kcal": 2200}},
            ),
            user="user-1",
        )

        self.assertEqual(result.status, AssistantToolStatus.BLOCKED)
        self.assertEqual(result.error_code, "non_draft_tool_blocked")
        self.assertEqual(result.metadata["details"]["category"], "validation")

    def test_maps_internal_tool_error(self):
        def update_profile_draft(user, *, updates, current_draft=None, field_sources=None):
            return tool_error(code="profile_draft_updates_required", message="updates required")

        result = execute_profile_draft_tool(
            AssistantToolRequest(
                tool_name=TOOL_UPDATE_PROFILE_DRAFT,
                arguments={"updates": {}},
            ),
            user="user-1",
            executor=ProfileDraftToolExecutor(dispatch_table={TOOL_UPDATE_PROFILE_DRAFT: update_profile_draft}),
        )

        self.assertEqual(result.status, AssistantToolStatus.ERROR)
        self.assertEqual(result.error_code, "profile_draft_updates_required")
        self.assertFalse(result.metadata["writes_allowed"])
