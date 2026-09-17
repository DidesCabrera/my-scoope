from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from notas.application.ai_tools.results import tool_success
from notas.application.ai_tools.workspace_query_tools import query_workspace_tool


class WorkspaceQueryToolTests(SimpleTestCase):
    def test_program_collection_routes_to_canonical_library_query(self):
        user = SimpleNamespace(is_authenticated=True)
        expected_data = {
            "resource": "programs",
            "scope": "library",
            "programs": [{"id": 7, "name": "Programa activo"}],
            "total_count": 1,
        }

        with patch(
            "notas.application.ai_tools.workspace_query_tools._query_library_collection_data",
            return_value=expected_data,
        ) as query_library:
            result = query_workspace_tool(
                user,
                resource="programs",
                search="activo",
                limit=12,
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.data, expected_data)
        query_library.assert_called_once_with(
            user,
            resource="programs",
            search="activo",
            limit=12,
            offset=0,
        )

    def test_program_detail_routes_to_existing_detail_query(self):
        user = object()
        expected = tool_success({"program": {"id": 7, "name": "Programa activo"}})

        with patch(
            "notas.application.ai_tools.workspace_query_tools.read_program_tool",
            return_value=expected,
        ) as read_program:
            result = query_workspace_tool(user, resource="programs", object_id=7)

        self.assertEqual(result, expected)
        read_program.assert_called_once_with(user, program_id=7)

    def test_unknown_resource_fails_without_dispatch(self):
        result = query_workspace_tool(object(), resource="anything")

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "invalid_workspace_resource")
