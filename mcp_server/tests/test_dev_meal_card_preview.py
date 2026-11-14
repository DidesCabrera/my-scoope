import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp_server.dev_meal_card_preview import (
    create_preview_server,
    current_css,
    preview_html,
    SAMPLE_FOOD,
    SAMPLE_DAILYPLAN,
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
        self.assertEqual(set(tools), {"preview_meal_card", "preview_food_card", "preview_dailyplan_card", "preview_card_styles"})
        self.assertEqual(tools["preview_card_styles"].meta["ui"]["visibility"], ["app"])
        self.assertTrue(uri.startswith("ui://myscoope-dev/meal-card-"))
        self.assertEqual(resource.mime_type, "text/html;profile=mcp-app")
        self.assertIn('name: "preview_card_styles"', resource.content)
        self.assertEqual(len(result["data"]["meal"]["foods"]), 4)
        self.assertEqual(result["data"]["meal"]["id"], 0)

    def test_entity_previews_are_synthetic_and_share_the_card(self):
        async def inspect():
            server = create_preview_server()
            tools = {tool.name: tool for tool in await server.list_tools()}
            food_uri = tools["preview_food_card"].meta["ui"]["resourceUri"]
            plan_uri = tools["preview_dailyplan_card"].meta["ui"]["resourceUri"]
            resource = (await server.read_resource(food_uri))[0]
            _, food_result = await server.call_tool("preview_food_card", {})
            _, plan_result = await server.call_tool("preview_dailyplan_card", {})
            return food_uri, plan_uri, resource, food_result, plan_result

        food_uri, plan_uri, resource, food_result, plan_result = asyncio.run(inspect())
        self.assertEqual(food_uri, plan_uri)
        self.assertIn('name: "preview_card_styles"', resource.content)
        self.assertEqual(food_result, SAMPLE_FOOD)
        self.assertEqual(plan_result, SAMPLE_DAILYPLAN)
        self.assertEqual(food_result["data"]["food"]["id"], 0)
        self.assertEqual(plan_result["data"]["dailyplan"]["id"], 0)

    def test_css_reads_editable_source_each_time(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "card.html"
            with patch("mcp_server.dev_meal_card_preview.SOURCE_PATH", source):
                source.write_text("<style>body{color:red}</style>", encoding="utf-8")
                self.assertEqual(current_css(), "body{color:red}")
                source.write_text("<style>body{color:blue}</style>", encoding="utf-8")
                self.assertEqual(current_css(), "body{color:blue}")

    def test_live_preview_keeps_existing_card_bridge(self):
        html = preview_html()
        self.assertIn('method: "ui/initialize"', html)
        self.assertIn('method: "tools/call"', html)
        self.assertIn('method: "ui/notifications/size-changed"', html)


if __name__ == "__main__":
    unittest.main()
