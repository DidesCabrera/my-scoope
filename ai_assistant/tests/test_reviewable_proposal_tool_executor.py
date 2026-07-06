from django.test import SimpleTestCase

from ai_assistant.application.tools import (
    ReviewableProposalToolExecutor,
    TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
    TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL,
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
    TOOL_READ_DAILYPLAN,
    execute_reviewable_proposal_tool,
)
from ai_assistant.domain.contracts import AssistantToolRequest, AssistantToolStatus
from notas.application.ai_tools.results import tool_error, tool_success


class ReviewableProposalToolExecutorTests(SimpleTestCase):
    def test_executes_reviewable_proposal_tool_through_dispatch_table(self):
        calls = []

        def create_meal_proposal(user, *, dailyplan_id, title, proposed_payload, targets=None, summary=""):
            calls.append((user, dailyplan_id, title, proposed_payload, targets, summary))
            return tool_success(
                {
                    "proposal": {
                        "id": 77,
                        "title": title,
                        "status": "pending_review",
                        "proposal_type": "meal",
                    }
                }
            )

        executor = ReviewableProposalToolExecutor(
            dispatch_table={TOOL_CREATE_VALIDATED_MEAL_PROPOSAL: create_meal_proposal}
        )

        result = executor.execute(
            AssistantToolRequest(
                tool_name=TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
                arguments={
                    "dailyplan_id": 12,
                    "title": "Almuerzo alto en proteína",
                    "proposed_payload": {"foods": [{"food_id": 1, "grams": 120}]},
                    "targets": {"kcal": 700},
                    "summary": "Ajuste sugerido por AI.",
                },
                request_id="proposal_1",
            ),
            user="user-1",
        )

        self.assertEqual(result.status, AssistantToolStatus.OK)
        self.assertEqual(result.tool_name, TOOL_CREATE_VALIDATED_MEAL_PROPOSAL)
        self.assertEqual(result.request_id, "proposal_1")
        self.assertEqual(result.data["proposal"]["id"], 77)
        self.assertEqual(result.metadata["executor"], "reviewable_proposal_tool_executor.v1")
        self.assertTrue(result.metadata["requires_human_review"])
        self.assertTrue(result.metadata["creates_reviewable_proposal"])
        self.assertFalse(result.metadata["applies_changes"])
        self.assertFalse(result.metadata["writes_allowed"])
        self.assertEqual(result.metadata["proposal_ids"], [77])
        self.assertEqual(calls[0][0], "user-1")

    def test_blocks_non_proposal_tool(self):
        executor = ReviewableProposalToolExecutor(
            dispatch_table={TOOL_READ_DAILYPLAN: lambda user, **kwargs: tool_success({})}
        )

        result = executor.execute(
            AssistantToolRequest(
                tool_name=TOOL_READ_DAILYPLAN,
                arguments={"dailyplan_id": 12},
            ),
            user="user-1",
        )

        self.assertEqual(result.status, AssistantToolStatus.BLOCKED)
        self.assertEqual(result.error_code, "non_reviewable_proposal_tool_blocked")
        self.assertEqual(result.metadata["details"]["category"], "read")
        self.assertFalse(result.metadata["applies_changes"])

    def test_blocks_forbidden_catalog_argument_before_dispatch(self):
        calls = []

        def create_build_proposal(user, **kwargs):
            calls.append(kwargs)
            return tool_success({})

        executor = ReviewableProposalToolExecutor(
            dispatch_table={TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL: create_build_proposal}
        )

        result = executor.execute(
            AssistantToolRequest(
                tool_name=TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
                arguments={
                    "dailyplan_id": 12,
                    "title": "Plan",
                    "proposed_payload": {"meals": [{"catalog_food_id": 99}]},
                },
            ),
            user="user-1",
        )

        self.assertEqual(result.status, AssistantToolStatus.BLOCKED)
        self.assertEqual(result.error_code, "forbidden_catalog_reference")
        self.assertEqual(calls, [])

    def test_maps_internal_tool_error_without_exposing_exception_payloads(self):
        def create_meal_proposal(user, **kwargs):
            return tool_error(
                code="validation_failed",
                message="La propuesta no cumple las reglas nutricionales.",
                details={"field": "proposed_payload"},
            )

        executor = ReviewableProposalToolExecutor(
            dispatch_table={TOOL_CREATE_VALIDATED_MEAL_PROPOSAL: create_meal_proposal}
        )

        result = execute_reviewable_proposal_tool(
            AssistantToolRequest(
                tool_name=TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
                arguments={
                    "dailyplan_id": 12,
                    "title": "Meal",
                    "proposed_payload": {},
                },
            ),
            user="user-1",
            executor=executor,
        )

        self.assertEqual(result.status, AssistantToolStatus.ERROR)
        self.assertEqual(result.error_code, "validation_failed")
        self.assertEqual(result.metadata["details"], {"field": "proposed_payload"})
        self.assertFalse(result.metadata["applies_changes"])

    def test_default_dispatch_table_contains_only_reviewable_proposal_tools(self):
        from ai_assistant.application.tools.proposal_executor import (
            build_default_reviewable_proposal_tool_dispatch_table,
        )

        table = build_default_reviewable_proposal_tool_dispatch_table()

        self.assertIn(TOOL_CREATE_VALIDATED_MEAL_PROPOSAL, table)
        self.assertIn(TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL, table)
        self.assertIn(TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL, table)
        self.assertNotIn(TOOL_READ_DAILYPLAN, table)
        self.assertNotIn("apply_proposal", table)
        self.assertNotIn("create_food", table)
