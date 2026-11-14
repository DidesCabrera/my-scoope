import unittest

from ai_assistant.application.tools.registry import list_mcp_tool_specs

from myscoope_mcp.tools import (
    FORBIDDEN_TOOL_NAMES,
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_LIST_USER_PROPOSALS,
    TOOL_LIST_FOOD_CATALOG,
    TOOL_READ_DAILYPLAN,
    TOOL_READ_MEAL,
    TOOL_READ_PROPOSAL,
    TOOL_SEARCH_USER_MEALS,
    get_tool_spec,
    is_forbidden_tool_name,
    list_allowed_tool_specs,
)


class MCPToolRegistryTests(unittest.TestCase):
    def test_projection_matches_canonical_contract_for_every_exposed_capability(self):
        canonical = {spec.mcp_name: spec for spec in list_mcp_tool_specs()}
        projected = {spec.name: spec for spec in list_allowed_tool_specs()}

        self.assertEqual(set(projected), set(canonical))
        for name, tool in projected.items():
            with self.subTest(tool=name):
                source = canonical[name]
                self.assertEqual(tool.description, source.description)
                self.assertEqual(tool.api_path, source.mcp_api_path)
                self.assertEqual(tool.input_schema, source.mcp_input_schema or source.input_schema)

    def test_allowed_tools_are_exactly_the_mvp_surface(self):
        tools = list_allowed_tool_specs()

        tool_names = {
            tool.name
            for tool in tools
        }

        self.assertEqual(
            tool_names,
            {
                TOOL_READ_DAILYPLAN,
                TOOL_READ_MEAL,
                TOOL_READ_PROPOSAL,
                TOOL_SEARCH_USER_MEALS,
                TOOL_LIST_USER_PROPOSALS,
                TOOL_LIST_FOOD_CATALOG,
                TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
                TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
                TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
                TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
                TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
                TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
            },
        )

    def test_allowed_tools_map_to_api_adapter_paths(self):
        checks = {
            TOOL_READ_DAILYPLAN: "/ai-tools/read-dailyplan/",
            TOOL_READ_MEAL: "/ai-tools/read-meal/",
            TOOL_READ_PROPOSAL: "/ai-tools/read-proposal/",
            TOOL_SEARCH_USER_MEALS: "/ai-tools/search-user-meals/",
            TOOL_LIST_USER_PROPOSALS: "/ai-tools/list-user-proposals/",
            TOOL_LIST_FOOD_CATALOG: "/ai-tools/list-food-catalog/",
            TOOL_COMPARE_DAILYPLAN_TO_TARGETS: "/ai-tools/compare-dailyplan-to-targets/",
            TOOL_CREATE_VALIDATED_MEAL_PROPOSAL: "/ai-tools/create-validated-meal-proposal/",
            TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL: "/ai-tools/create-validated-dailyplan-proposal/",
            TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL: "/ai-tools/create-validated-dailyplan-build-proposal/",
            TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: "/ai-tools/create-nutrition-engine-dailyplan-proposal/",
            TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: "/ai-tools/iterate-nutrition-engine-dailyplan-proposal/",
        }

        for tool_name, expected_path in checks.items():
            spec = get_tool_spec(tool_name)

            self.assertEqual(
                spec.api_path,
                expected_path,
            )

    def test_forbidden_tools_are_not_registered(self):
        allowed_tool_names = {
            tool.name
            for tool in list_allowed_tool_specs()
        }

        for forbidden_tool_name in FORBIDDEN_TOOL_NAMES:
            self.assertNotIn(
                forbidden_tool_name,
                allowed_tool_names,
            )
            self.assertTrue(
                is_forbidden_tool_name(forbidden_tool_name),
            )

    def test_apply_tools_are_explicitly_forbidden(self):
        apply_tool_names = {
            "apply_approved_proposal",
            "apply_proposal",
            "apply_validated_proposal",
        }

        for tool_name in apply_tool_names:
            self.assertTrue(
                is_forbidden_tool_name(tool_name),
            )

    def test_unknown_tool_raises_stable_error(self):
        with self.assertRaisesRegex(
            ValueError,
            "unsupported_mcp_tool:unknown_tool",
        ):
            get_tool_spec("unknown_tool")


if __name__ == "__main__":
    unittest.main()
