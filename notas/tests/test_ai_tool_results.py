import json

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.test import SimpleTestCase

from notas.application.ai_tools.errors import map_exception_to_tool_error
from notas.application.ai_tools.results import (
    AIToolError,
    AIToolResult,
    tool_error,
    tool_success,
)
from notas.application.ai_tools.runtime import run_ai_tool


def assert_json_serializable(test_case, value):
    try:
        json.dumps(value)
    except TypeError as exc:
        test_case.fail(f"Value is not JSON serializable: {exc}")


class AIToolResultTests(SimpleTestCase):
    def test_tool_success_returns_serializable_contract(self):
        result = tool_success(
            data={
                "dailyplan_id": 123,
                "name": "Training Day",
            },
        )

        self.assertIsInstance(result, AIToolResult)
        self.assertTrue(result.ok)
        self.assertEqual(
            result.data,
            {
                "dailyplan_id": 123,
                "name": "Training Day",
            },
        )
        self.assertIsNone(result.error)

        data = result.as_dict()

        self.assertEqual(
            data,
            {
                "ok": True,
                "data": {
                    "dailyplan_id": 123,
                    "name": "Training Day",
                },
                "error": None,
            },
        )

        assert_json_serializable(
            self,
            data,
        )

    def test_tool_error_returns_serializable_contract(self):
        result = tool_error(
            code="dailyplan_not_found",
            message="DailyPlan is not available for this user.",
            details={
                "dailyplan_id": 123,
            },
        )

        self.assertIsInstance(result, AIToolResult)
        self.assertFalse(result.ok)
        self.assertEqual(result.data, {})
        self.assertIsInstance(result.error, AIToolError)

        data = result.as_dict()

        self.assertEqual(
            data,
            {
                "ok": False,
                "data": {},
                "error": {
                    "code": "dailyplan_not_found",
                    "message": "DailyPlan is not available for this user.",
                    "details": {
                        "dailyplan_id": 123,
                    },
                },
            },
        )

        assert_json_serializable(
            self,
            data,
        )

    def test_map_http404_to_tool_error(self):
        result = map_exception_to_tool_error(
            Http404("Not found"),
        )

        data = result.as_dict()

        self.assertFalse(data["ok"])
        self.assertEqual(data["error"]["code"], "not_found")
        self.assertEqual(
            data["error"]["message"],
            "The requested resource was not found or is not available for this user.",
        )

        assert_json_serializable(
            self,
            data,
        )

    def test_map_object_does_not_exist_to_tool_error(self):
        result = map_exception_to_tool_error(
            ObjectDoesNotExist("Object not found"),
        )

        data = result.as_dict()

        self.assertFalse(data["ok"])
        self.assertEqual(data["error"]["code"], "not_found")
        self.assertEqual(
            data["error"]["message"],
            "The requested resource was not found or is not available for this user.",
        )

        assert_json_serializable(
            self,
            data,
        )

    def test_map_value_error_to_tool_error(self):
        result = map_exception_to_tool_error(
            ValueError("proposal_is_not_applicable"),
        )

        data = result.as_dict()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "proposal_is_not_applicable",
        )
        self.assertEqual(
            data["error"]["message"],
            "The requested operation is not valid.",
        )

        assert_json_serializable(
            self,
            data,
        )

    def test_map_unexpected_exception_to_tool_error(self):
        result = map_exception_to_tool_error(
            RuntimeError("Boom"),
        )

        data = result.as_dict()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "unexpected_error",
        )

        assert_json_serializable(
            self,
            data,
        )

    def test_run_ai_tool_wraps_success(self):
        def fake_tool():
            return {
                "value": 123,
            }

        result = run_ai_tool(
            fake_tool,
            require_auth=False,
        )

        data = result.as_dict()

        self.assertTrue(data["ok"])
        self.assertEqual(
            data["data"],
            {
                "value": 123,
            },
        )
        self.assertIsNone(data["error"])

        assert_json_serializable(
            self,
            data,
        )

    def test_run_ai_tool_wraps_known_error(self):
        def fake_tool():
            raise ValueError("invalid_targets")

        result = run_ai_tool(
            fake_tool,
            require_auth=False,
        )

        data = result.as_dict()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "invalid_targets",
        )

        assert_json_serializable(
            self,
            data,
        )

    def test_run_ai_tool_requires_user_by_default(self):
        def fake_tool():
            return {
                "value": 123,
            }

        result = run_ai_tool(fake_tool)

        data = result.as_dict()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "tool_user_required",
        )

        assert_json_serializable(
            self,
            data,
        )

    def test_run_ai_tool_rejects_anonymous_user(self):
        class AnonymousUserLike:
            is_authenticated = False

        def fake_tool():
            return {
                "value": 123,
            }

        result = run_ai_tool(
            fake_tool,
            user=AnonymousUserLike(),
        )

        data = result.as_dict()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "tool_user_not_authenticated",
        )

        assert_json_serializable(
            self,
            data,
        )