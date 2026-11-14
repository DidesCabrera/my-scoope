import unittest

from myscoope_mcp.contracts import MCPToolCallResult
from myscoope_mcp.tool_handlers import (
    call_read_tool,
    list_user_proposals,
    read_dailyplan,
    read_meal,
    read_proposal,
    search_user_meals,
)
from myscoope_mcp.tools import (
    TOOL_LIST_USER_PROPOSALS,
    TOOL_READ_DAILYPLAN,
    TOOL_READ_MEAL,
    TOOL_READ_PROPOSAL,
    TOOL_SEARCH_USER_MEALS,
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


class MCPReadToolHandlerTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeMyscoopeAPIClient()

    def test_read_dailyplan_calls_api_adapter(self):
        result = read_dailyplan(
            self.client,
            dailyplan_id=123,
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

    def test_read_proposal_calls_api_adapter(self):
        result = read_proposal(
            self.client,
            proposal_id=456,
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

    def test_read_meal_calls_existing_authorized_api_adapter(self):
        result = read_meal(self.client, meal_id=23)
        self.assertTrue(result.ok)
        self.assertEqual(self.client.calls, [{
            "api_path": "/ai-tools/read-meal/",
            "payload": {"meal_id": 23},
        }])

    def test_read_meal_requires_id_before_api_call(self):
        result = call_read_tool(self.client, TOOL_READ_MEAL, {})
        self.assertFalse(result.ok)
        self.assertEqual(result.error["code"], "missing_required_argument:meal_id")
        self.assertEqual(self.client.calls, [])

    def test_search_user_meals_uses_bounded_api_adapter(self):
        result = search_user_meals(self.client, query="almuerzo", limit=3)
        self.assertTrue(result.ok)
        self.assertEqual(self.client.calls, [{
            "api_path": "/ai-tools/search-user-meals/",
            "payload": {"query": "almuerzo", "limit": 3},
        }])

    def test_search_user_meals_requires_query_before_api_call(self):
        result = call_read_tool(self.client, TOOL_SEARCH_USER_MEALS, {})
        self.assertFalse(result.ok)
        self.assertEqual(result.error["code"], "missing_required_argument:query")
        self.assertEqual(self.client.calls, [])

    def test_list_user_proposals_calls_api_adapter(self):
        result = list_user_proposals(
            self.client,
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

    def test_call_read_tool_dispatches_read_dailyplan(self):
        result = call_read_tool(
            self.client,
            TOOL_READ_DAILYPLAN,
            {
                "dailyplan_id": 123,
            },
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            self.client.calls[0]["api_path"],
            "/ai-tools/read-dailyplan/",
        )

    def test_call_read_tool_dispatches_read_proposal(self):
        result = call_read_tool(
            self.client,
            TOOL_READ_PROPOSAL,
            {
                "proposal_id": 456,
            },
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            self.client.calls[0]["api_path"],
            "/ai-tools/read-proposal/",
        )

    def test_call_read_tool_dispatches_list_user_proposals(self):
        result = call_read_tool(
            self.client,
            TOOL_LIST_USER_PROPOSALS,
            {},
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            self.client.calls[0]["api_path"],
            "/ai-tools/list-user-proposals/",
        )

    def test_call_read_tool_requires_dailyplan_id(self):
        result = call_read_tool(
            self.client,
            TOOL_READ_DAILYPLAN,
            {},
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

    def test_call_read_tool_requires_proposal_id(self):
        result = call_read_tool(
            self.client,
            TOOL_READ_PROPOSAL,
            {},
        )

        data = result.as_dict()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "missing_required_argument:proposal_id",
        )
        self.assertEqual(
            self.client.calls,
            [],
        )

    def test_call_read_tool_rejects_unknown_read_tool(self):
        result = call_read_tool(
            self.client,
            "unknown_read_tool",
            {},
        )

        data = result.as_dict()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "unsupported_read_tool:unknown_read_tool",
        )
        self.assertEqual(
            self.client.calls,
            [],
        )


if __name__ == "__main__":
    unittest.main()
