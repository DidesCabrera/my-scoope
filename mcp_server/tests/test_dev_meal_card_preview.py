import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp_server.dev_meal_card_preview import (
    ENTITY_CARD_URI,
    MEAL_CARD_URI,
    PROBE_CARD_URI,
    SAMPLE_DAILYPLAN,
    SAMPLE_FOOD,
    create_preview_server,
    current_css,
    preview_html,
)


class DevMealCardPreviewTests(unittest.TestCase):
    def test_server_exposes_only_synthetic_preview_and_app_css_tool(self):
        async def inspect():
            server = create_preview_server()
            tools = {tool.name: tool for tool in await server.list_tools()}
            uri = tools["preview_meal_card"].meta["ui"]["resourceUri"]
            resource = (await server.read_resource(uri))[0]
            _, result = await server.call_tool("preview_meal_card", {})
            return tools, uri, resource, result

        tools, uri, resource, result = asyncio.run(inspect())
        self.assertTrue(create_preview_server().settings.json_response)
        self.assertEqual(set(tools), {"preview_meal_card", "preview_food_card", "preview_dailyplan_card", "preview_minimal_card", "preview_minimal_card_v2", "preview_card_styles"})
        self.assertEqual(tools["preview_card_styles"].meta["ui"]["visibility"], ["app"])
        self.assertEqual(uri, MEAL_CARD_URI)
        self.assertEqual(tools["preview_meal_card"].meta["openai/outputTemplate"], uri)
        self.assertEqual(resource.mime_type, "text/html;profile=mcp-app")
        self.assertIn('name: "preview_card_styles"', resource.content)
        self.assertEqual(len(result["data"]["meal"]["foods"]), 4)
        self.assertEqual(result["data"]["meal"]["id"], 0)

    def test_entity_previews_are_synthetic_and_versioned_separately(self):
        async def inspect():
            server = create_preview_server()
            tools = {tool.name: tool for tool in await server.list_tools()}
            food_uri = tools["preview_food_card"].meta["ui"]["resourceUri"]
            plan_uri = tools["preview_dailyplan_card"].meta["ui"]["resourceUri"]
            resource = (await server.read_resource(food_uri))[0]
            plan_resource = (await server.read_resource(plan_uri))[0]
            _, food_result = await server.call_tool("preview_food_card", {})
            _, plan_result = await server.call_tool("preview_dailyplan_card", {})
            return tools, food_uri, plan_uri, resource, plan_resource, food_result, plan_result

        tools, food_uri, plan_uri, resource, plan_resource, food_result, plan_result = asyncio.run(inspect())
        self.assertEqual(food_uri, ENTITY_CARD_URI)
        self.assertNotEqual(food_uri, plan_uri)
        self.assertEqual(tools["preview_food_card"].meta["openai/outputTemplate"], food_uri)
        self.assertEqual(tools["preview_dailyplan_card"].meta["openai/outputTemplate"], plan_uri)
        self.assertIn('name: "preview_card_styles"', resource.content)
        self.assertIn('id="detail-link"', plan_resource.content)
        self.assertIn('"http://127.0.0.1:8000/app"', plan_resource.content)
        self.assertEqual(food_result, SAMPLE_FOOD)
        self.assertEqual(plan_result, SAMPLE_DAILYPLAN)
        self.assertEqual(food_result["data"]["food"]["id"], 0)
        self.assertEqual(plan_result["data"]["dailyplan"]["id"], 42)

    def test_css_reads_editable_source_each_time(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "card.html"
            with patch("mcp_server.dev_meal_card_preview.SOURCE_PATH", source):
                source.write_text("<style>body{color:red}</style>", encoding="utf-8")
                self.assertEqual(current_css(), "body{color:red}")
                source.write_text("<style>body{color:blue}</style>", encoding="utf-8")
                self.assertEqual(current_css(), "body{color:blue}")

    def test_minimal_card_has_visible_content_and_minimal_bridge(self):
        async def inspect():
            server = create_preview_server()
            tools = {tool.name: tool for tool in await server.list_tools()}
            uri = tools["preview_minimal_card"].meta["ui"]["resourceUri"]
            resource = (await server.read_resource(uri))[0]
            _, result = await server.call_tool("preview_minimal_card", {})
            _, v2_result = await server.call_tool("preview_minimal_card_v2", {})
            return tools, uri, resource, result, v2_result

        tools, uri, resource, result, v2_result = asyncio.run(inspect())
        self.assertEqual(tools["preview_minimal_card"].meta["openai/outputTemplate"], uri)
        self.assertEqual(tools["preview_minimal_card_v2"].meta["ui"]["resourceUri"], uri)
        self.assertEqual(resource.mime_type, "text/html;profile=mcp-app")
        self.assertIn("Vista mínima MCP visible", resource.content)
        self.assertIn('method:"ui/initialize"', resource.content)
        self.assertIn('method:"ui/notifications/initialized"', resource.content)
        self.assertEqual(result["data"]["message"], "Vista mínima MCP")
        self.assertEqual(v2_result["data"]["message"], "Vista mínima MCP v2")

    def test_live_preview_keeps_existing_card_bridge(self):
        html = preview_html()
        self.assertIn('method: "ui/initialize"', html)
        self.assertIn('method: "tools/call"', html)
        self.assertIn('method: "ui/notifications/size-changed"', html)

    def test_resource_uris_survive_restart_and_previous_random_uris_remain_readable(self):
        async def inspect():
            before_restart = create_preview_server()
            after_restart = create_preview_server()
            old_version = "8c29a2b83a154b5393ce1f10ceb23cc5"
            expected = {
                "preview_meal_card": (MEAL_CARD_URI, f"ui://myscoope-dev/meal-card-{old_version}.html", "preview_card_styles"),
                "preview_food_card": (ENTITY_CARD_URI, f"ui://myscoope-dev/entity-card-{old_version}.html", "preview_card_styles"),
                "preview_minimal_card": (PROBE_CARD_URI, f"ui://myscoope-dev/probe-card-{old_version}.html", "Vista mínima MCP visible"),
            }
            before_tools = {tool.name: tool for tool in await before_restart.list_tools()}
            after_tools = {tool.name: tool for tool in await after_restart.list_tools()}
            for tool_name, (stable_uri, old_uri, expected_text) in expected.items():
                self.assertEqual(before_tools[tool_name].meta["ui"]["resourceUri"], stable_uri)
                self.assertEqual(after_tools[tool_name].meta["ui"]["resourceUri"], stable_uri)
                for resource_uri in (stable_uri, old_uri):
                    resource = (await after_restart.read_resource(resource_uri))[0]
                    self.assertEqual(resource.mime_type, "text/html;profile=mcp-app")
                    self.assertIn(expected_text, resource.content)

        asyncio.run(inspect())


if __name__ == "__main__":
    unittest.main()
