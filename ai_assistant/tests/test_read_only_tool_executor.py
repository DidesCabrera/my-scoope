from django.test import SimpleTestCase

from ai_assistant.application.tools import (
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
    TOOL_LIST_OPERATIONAL_FOODS,
    TOOL_LIST_SAVED_COMPARISONS,
    TOOL_LIST_USER_PROPOSALS,
    TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES,
    TOOL_READ_DAILYPLAN,
    TOOL_READ_PROPOSAL,
    TOOL_READ_SAVED_COMPARISON,
    TOOL_SEARCH_OPERATIONAL_FOODS,
    ReadOnlyToolExecutor,
    ReadOnlyToolExecutorConfig,
    execute_read_only_tool,
)
from ai_assistant.domain.contracts import AssistantToolRequest, AssistantToolStatus
from notas.application.ai_tools.results import tool_error, tool_success


class ReadOnlyToolExecutorTests(SimpleTestCase):
    def test_executes_allowed_read_only_tool_through_dispatch_table(self):
        calls = []

        def read_dailyplan(user, *, dailyplan_id):
            calls.append((user, dailyplan_id))
            return tool_success({"dailyplan": {"id": dailyplan_id, "title": "Plan base"}})

        executor = ReadOnlyToolExecutor(dispatch_table={TOOL_READ_DAILYPLAN: read_dailyplan})

        result = executor.execute(
            AssistantToolRequest(
                tool_name="Read DailyPlan",
                arguments={"dailyplan_id": 123},
                request_id="call_1",
            ),
            user="user-1",
        )

        self.assertEqual(result.status, AssistantToolStatus.OK)
        self.assertEqual(result.tool_name, TOOL_READ_DAILYPLAN)
        self.assertEqual(result.request_id, "call_1")
        self.assertEqual(result.data["dailyplan"], {"id": 123, "title": "Plan base"})
        self.assertEqual(calls, [("user-1", 123)])
        self.assertEqual(result.metadata["executor"], "read_only_tool_executor.v1")
        self.assertFalse(result.metadata["writes_allowed"])

    def test_blocks_unknown_or_missing_argument_before_dispatch(self):
        calls = []

        def read_dailyplan(user, *, dailyplan_id):
            calls.append(dailyplan_id)
            return tool_success({})

        executor = ReadOnlyToolExecutor(dispatch_table={TOOL_READ_DAILYPLAN: read_dailyplan})
        unknown = executor.execute(
            AssistantToolRequest(tool_name="raw_sql", arguments={"query": "select 1"}),
            user="user-1",
        )
        missing = executor.execute(
            AssistantToolRequest(tool_name=TOOL_READ_DAILYPLAN, arguments={}),
            user="user-1",
        )

        self.assertEqual(unknown.status, AssistantToolStatus.BLOCKED)
        self.assertEqual(unknown.error_code, "forbidden_ai_assistant_tool")
        self.assertEqual(missing.status, AssistantToolStatus.BLOCKED)
        self.assertEqual(missing.error_code, "invalid_ai_assistant_tool_arguments")
        self.assertEqual(calls, [])

    def test_blocks_validation_and_proposal_tools_in_patch_53(self):
        executor = ReadOnlyToolExecutor(
            dispatch_table={
                TOOL_COMPARE_DAILYPLAN_TO_TARGETS: lambda user, **kwargs: tool_success({}),
                TOOL_CREATE_VALIDATED_MEAL_PROPOSAL: lambda user, **kwargs: tool_success({}),
            }
        )

        validation_result = executor.execute(
            AssistantToolRequest(
                tool_name=TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
                arguments={"dailyplan_id": 1, "targets": {"kcal": 2200}},
            ),
            user="user-1",
        )
        proposal_result = executor.execute(
            AssistantToolRequest(
                tool_name=TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
                arguments={"dailyplan_id": 1, "title": "Meal", "proposed_payload": {}},
            ),
            user="user-1",
        )

        self.assertEqual(validation_result.status, AssistantToolStatus.BLOCKED)
        self.assertEqual(validation_result.error_code, "non_read_only_tool_blocked")
        self.assertEqual(validation_result.metadata["details"]["category"], "validation")
        self.assertEqual(proposal_result.status, AssistantToolStatus.BLOCKED)
        self.assertEqual(proposal_result.error_code, "non_read_only_tool_blocked")
        self.assertEqual(proposal_result.metadata["details"]["category"], "proposal")

    def test_limits_operational_food_results_and_clamps_limit(self):
        def list_foods(user, *, limit):
            foods = [{"id": index, "name": f"Food {index}"} for index in range(1, 8)]
            return tool_success({"foods": foods, "limit_seen": limit})

        executor = ReadOnlyToolExecutor(
            dispatch_table={TOOL_LIST_OPERATIONAL_FOODS: list_foods},
            config=ReadOnlyToolExecutorConfig(default_limit=3, max_limit=5),
        )

        result = executor.execute(
            AssistantToolRequest(
                tool_name=TOOL_LIST_OPERATIONAL_FOODS,
                arguments={"limit": 999},
            ),
            user="user-1",
        )

        self.assertEqual(result.status, AssistantToolStatus.OK)
        self.assertEqual(len(result.data["foods"]), 5)
        self.assertEqual(result.data["limit_seen"], 5)
        self.assertEqual(result.data["limit"], 5)
        self.assertTrue(result.data["truncated"])

    def test_search_operational_foods_normalizes_query_and_limit(self):
        calls = []

        def search_foods(user, *, query, limit):
            calls.append((query, limit))
            return tool_success({"foods": [{"id": 1}, {"id": 2}, {"id": 3}]})

        executor = ReadOnlyToolExecutor(
            dispatch_table={TOOL_SEARCH_OPERATIONAL_FOODS: search_foods},
            config=ReadOnlyToolExecutorConfig(default_limit=2, max_limit=5),
        )

        result = executor.execute(
            AssistantToolRequest(
                tool_name=TOOL_SEARCH_OPERATIONAL_FOODS,
                arguments={"query": "  arroz  ", "limit": "2"},
            ),
            user="user-1",
        )

        self.assertEqual(result.status, AssistantToolStatus.OK)
        self.assertEqual(calls, [("arroz", 2)])
        self.assertEqual(len(result.data["foods"]), 2)

    def test_list_saved_comparisons_normalizes_kind_and_limit(self):
        calls = []

        def list_comparisons(user, *, kind=None, limit=20):
            calls.append((kind, limit))
            return tool_success({"saved_comparisons": [{"id": 1}, {"id": 2}, {"id": 3}]})

        executor = ReadOnlyToolExecutor(
            dispatch_table={TOOL_LIST_SAVED_COMPARISONS: list_comparisons},
            config=ReadOnlyToolExecutorConfig(default_limit=2, max_limit=5),
        )

        result = executor.execute(
            AssistantToolRequest(
                tool_name=TOOL_LIST_SAVED_COMPARISONS,
                arguments={"kind": "  DailyPlans  ", "limit": "2"},
            ),
            user="user-1",
        )

        self.assertEqual(result.status, AssistantToolStatus.OK)
        self.assertEqual(calls, [("dailyplans", 2)])
        self.assertEqual(len(result.data["saved_comparisons"]), 2)

    def test_dispatches_read_saved_comparison(self):
        calls = []

        def read_comparison(user, *, comparison_id):
            calls.append((user, comparison_id))
            return tool_success({"saved_comparison": {"id": comparison_id, "name": "Comparación"}})

        executor = ReadOnlyToolExecutor(dispatch_table={TOOL_READ_SAVED_COMPARISON: read_comparison})

        result = executor.execute(
            AssistantToolRequest(
                tool_name=TOOL_READ_SAVED_COMPARISON,
                arguments={"comparison_id": 12},
            ),
            user="user-1",
        )

        self.assertEqual(result.status, AssistantToolStatus.OK)
        self.assertEqual(result.data["saved_comparison"]["id"], 12)
        self.assertEqual(calls, [("user-1", 12)])


    def test_preview_solver_candidates_normalizes_arguments(self):
        calls = []

        def preview_candidates(user, *, search=None, limit=20, include_extended=True):
            calls.append((search, limit, include_extended))
            return tool_success({
                "solver_candidate_preview": {
                    "candidates": [{"food_id": 1}, {"food_id": 2}, {"food_id": 3}],
                }
            })

        executor = ReadOnlyToolExecutor(
            dispatch_table={TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES: preview_candidates},
            config=ReadOnlyToolExecutorConfig(default_limit=2, max_limit=5),
        )

        result = executor.execute(
            AssistantToolRequest(
                tool_name=TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES,
                arguments={"search": "  pollo  ", "limit": "4", "include_extended": "false"},
            ),
            user="user-1",
        )

        self.assertEqual(result.status, AssistantToolStatus.OK)
        self.assertEqual(calls, [("pollo", 4, False)])
        self.assertEqual(len(result.data["solver_candidate_preview"]["candidates"]), 3)
        self.assertFalse(result.metadata["writes_allowed"])

    def test_maps_internal_tool_error_without_exposing_exception_payloads(self):
        def list_proposals(user):
            return tool_error(
                code="permission_denied",
                message="No tienes permiso para ejecutar esta tool.",
                details={"model": "NutritionProposal"},
            )

        executor = ReadOnlyToolExecutor(dispatch_table={TOOL_LIST_USER_PROPOSALS: list_proposals})

        result = execute_read_only_tool(
            AssistantToolRequest(tool_name=TOOL_LIST_USER_PROPOSALS, arguments={}),
            user="user-1",
            executor=executor,
        )

        self.assertEqual(result.status, AssistantToolStatus.ERROR)
        self.assertEqual(result.error_code, "permission_denied")
        self.assertEqual(result.error_message, "No tienes permiso para ejecutar esta tool.")
        self.assertEqual(result.metadata["details"], {"model": "NutritionProposal"})
        self.assertFalse(result.metadata["writes_allowed"])

    def test_unconnected_read_only_tool_is_blocked(self):
        executor = ReadOnlyToolExecutor(
            dispatch_table={TOOL_READ_DAILYPLAN: lambda user, **kwargs: tool_success({})}
        )

        result = executor.execute(
            AssistantToolRequest(tool_name=TOOL_READ_PROPOSAL, arguments={"proposal_id": 1}),
            user="user-1",
        )

        self.assertEqual(result.status, AssistantToolStatus.BLOCKED)
        self.assertEqual(result.error_code, "read_only_tool_not_dispatchable")

    def test_dispatch_table_does_not_contain_food_catalog_tools(self):
        from ai_assistant.application.tools.executor import build_default_read_only_tool_dispatch_table

        table = build_default_read_only_tool_dispatch_table()

        self.assertIn(TOOL_READ_DAILYPLAN, table)
        self.assertIn(TOOL_SEARCH_OPERATIONAL_FOODS, table)
        self.assertIn(TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES, table)
        self.assertIn(TOOL_LIST_SAVED_COMPARISONS, table)
        self.assertIn(TOOL_READ_SAVED_COMPARISON, table)
        self.assertNotIn("list_food_catalog", table)
        self.assertNotIn("search_food_catalog", table)
