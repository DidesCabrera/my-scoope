import unittest

from myscoope_mcp.contracts import MCPToolCallResult
from myscoope_mcp.dispatcher import dispatch_tool_call
from myscoope_mcp.tools import (
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
    TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_LIST_USER_PROPOSALS,
    TOOL_READ_DAILYPLAN,
    TOOL_READ_PROPOSAL,
)


class FakeMyscoopeAPIClient:
    def __init__(self):
        self.calls = []

    def call_ai_tool_api(self, api_path, payload):
        self.calls.append(
            {
                "api_path": api_path,
                "payload": payload,
            }
        )

        return MCPToolCallResult(
            ok=True,
            data={
                "api_path": api_path,
                "payload": payload,
            },
            error=None,
        )


class MCPDispatcherTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeMyscoopeAPIClient()

    def test_dispatch_read_dailyplan(self):
        result = dispatch_tool_call(
            client=self.client,
            tool_name=TOOL_READ_DAILYPLAN,
            arguments={
                "dailyplan_id": 123,
            },
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            self.client.calls,
            [
                {
                    "api_path": "/ai-tools/read-dailyplan/",
                    "payload": {
                        "dailyplan_id": 123,
                    },
                }
            ],
        )

    def test_dispatch_read_proposal(self):
        result = dispatch_tool_call(
            client=self.client,
            tool_name=TOOL_READ_PROPOSAL,
            arguments={
                "proposal_id": 456,
            },
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            self.client.calls,
            [
                {
                    "api_path": "/ai-tools/read-proposal/",
                    "payload": {
                        "proposal_id": 456,
                    },
                }
            ],
        )

    def test_dispatch_list_user_proposals(self):
        result = dispatch_tool_call(
            client=self.client,
            tool_name=TOOL_LIST_USER_PROPOSALS,
            arguments={},
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            self.client.calls,
            [
                {
                    "api_path": "/ai-tools/list-user-proposals/",
                    "payload": {},
                }
            ],
        )

    def test_dispatch_validation_tool(self):
        result = dispatch_tool_call(
            client=self.client,
            tool_name=TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
            arguments={
                "dailyplan_id": 123,
                "targets": {
                    "protein": 190,
                },
            },
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            self.client.calls,
            [
                {
                    "api_path": "/ai-tools/compare-dailyplan-to-targets/",
                    "payload": {
                        "dailyplan_id": 123,
                        "targets": {
                            "protein": 190,
                        },
                    },
                }
            ],
        )

    def test_dispatch_proposal_tool(self):
        result = dispatch_tool_call(
            client=self.client,
            tool_name=TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
            arguments={
                "dailyplan_id": 123,
                "title": "AI protein proposal",
                "targets": {
                    "protein": 190,
                },
            },
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            self.client.calls,
            [
                {
                    "api_path": "/ai-tools/create-validated-dailyplan-proposal/",
                    "payload": {
                        "dailyplan_id": 123,
                        "title": "AI protein proposal",
                        "targets": {
                            "protein": 190,
                        },
                    },
                }
            ],
        )


    def test_dispatch_create_nutrition_engine_dailyplan_proposal(self):
        brief = {
            "raw_prompt": "quiero bajar grasa, simple",
            "goal": "fat_loss",
            "requested_entity": "daily_plan",
            "meals_per_day": 4,
        }

        result = dispatch_tool_call(
            client=self.client,
            tool_name=TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
            arguments={
                "nutrition_brief": brief,
            },
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            self.client.calls,
            [
                {
                    "api_path": "/ai-tools/create-nutrition-engine-dailyplan-proposal/",
                    "payload": {
                        "nutrition_brief": brief,
                    },
                }
            ],
        )

    def test_dispatch_iterate_nutrition_engine_dailyplan_proposal(self):
        brief = {
            "raw_prompt": "quiero bajar grasa, simple",
            "goal": "fat_loss",
            "requested_entity": "daily_plan",
            "meals_per_day": 4,
        }

        result = dispatch_tool_call(
            client=self.client,
            tool_name=TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
            arguments={
                "previous_proposal_id": 456,
                "nutrition_brief": brief,
                "user_message": "sin arroz",
            },
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            self.client.calls,
            [
                {
                    "api_path": "/ai-tools/iterate-nutrition-engine-dailyplan-proposal/",
                    "payload": {
                        "previous_proposal_id": 456,
                        "nutrition_brief": brief,
                        "user_message": "sin arroz",
                    },
                }
            ],
        )

    def test_dispatch_blocks_forbidden_apply_tool(self):
        result = dispatch_tool_call(
            client=self.client,
            tool_name="apply_approved_proposal",
            arguments={
                "proposal_id": 999,
            },
        )

        data = result.as_dict()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "forbidden_mcp_tool:apply_approved_proposal",
        )
        self.assertEqual(
            self.client.calls,
            [],
        )

    def test_dispatch_blocks_forbidden_raw_command_execution(self):
        result = dispatch_tool_call(
            client=self.client,
            tool_name="raw_command_execution",
            arguments={
                "command": "dangerous",
            },
        )

        data = result.as_dict()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "forbidden_mcp_tool:raw_command_execution",
        )
        self.assertEqual(
            self.client.calls,
            [],
        )

    def test_dispatch_rejects_unknown_tool(self):
        result = dispatch_tool_call(
            client=self.client,
            tool_name="unknown_tool",
            arguments={},
        )

        data = result.as_dict()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "unsupported_mcp_tool:unknown_tool",
        )
        self.assertEqual(
            self.client.calls,
            [],
        )

    def test_dispatch_preserves_missing_argument_errors(self):
        result = dispatch_tool_call(
            client=self.client,
            tool_name=TOOL_READ_DAILYPLAN,
            arguments={},
        )

        data = result.as_dict()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "missing_required_argument:dailyplan_id",
        )
        self.assertEqual(
            self.client.calls,
            [],
        )


if __name__ == "__main__":
    unittest.main()