from django.test import SimpleTestCase

from ai_assistant.application.tools import (
    TOOL_COMMIT_PROFILE_UPDATE,
    ProfileCommitToolExecutor,
    execute_profile_commit_tool,
)
from ai_assistant.domain import AssistantToolRequest, AssistantToolStatus
from notas.application.ai_tools.results import tool_success


class ProfileCommitToolExecutorTests(SimpleTestCase):
    def test_blocks_commit_without_trusted_user_approval_metadata(self):
        result = execute_profile_commit_tool(
            AssistantToolRequest(
                tool_name=TOOL_COMMIT_PROFILE_UPDATE,
                arguments={"profile_draft": {"height_cm": 188}},
                request_id="commit_1",
            ),
            user=object(),
            executor=ProfileCommitToolExecutor(
                dispatch_table={TOOL_COMMIT_PROFILE_UPDATE: lambda user, **kwargs: tool_success({})}
            ),
        )

        self.assertEqual(result.status, AssistantToolStatus.BLOCKED)
        self.assertEqual(result.error_code, "profile_commit_requires_trusted_user_approval")
        self.assertFalse(result.metadata["writes_allowed"])

    def test_executes_commit_with_trusted_user_approval_metadata(self):
        def commit_tool(user, *, profile_draft, approved_fields=None):
            return tool_success(
                {
                    "profile_draft": profile_draft,
                    "updated_fields": ["height_cm"],
                    "unchanged_fields": [],
                    "skipped_fields": {},
                    "source_boundary": {"persistent_profile_updated": True},
                }
            )

        result = execute_profile_commit_tool(
            AssistantToolRequest(
                tool_name=TOOL_COMMIT_PROFILE_UPDATE,
                arguments={"profile_draft": {"height_cm": 188}},
                request_id="commit_2",
                metadata={"approved_by_user": True, "approval_source": "profile_card_button"},
            ),
            user=object(),
            executor=ProfileCommitToolExecutor(dispatch_table={TOOL_COMMIT_PROFILE_UPDATE: commit_tool}),
        )

        self.assertEqual(result.status, AssistantToolStatus.OK)
        self.assertTrue(result.metadata["writes_allowed"])
        self.assertTrue(result.metadata["persistent_profile_updated"])
        self.assertEqual(result.metadata["approval_source"], "profile_card_button")
