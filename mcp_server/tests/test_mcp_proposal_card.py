import asyncio
import unittest
from unittest.mock import patch

from myscoope_mcp.contracts import MCPToolCallResult
from myscoope_mcp.proposal_card import build_proposal_card_data
from myscoope_mcp.protocol_server import (
    PROPOSAL_CARD_RESOURCE_URI,
    create_mcp_server,
    summarize_generated_dailyplan_proposal_result,
)


def proposal_detail():
    return {
        "id": 26,
        "status": "pending_review",
        "title": "Persona 70 kg",
        "summary": "Mujer de 30 años",
        "current_snapshot": {"weight_kg": 70},
        "audit_events": [{"private": "do not send"}],
        "validation_summary": {
            "simulation": {
                "dailyplan": {
                    "name": "Día de mantenimiento",
                    "kpis": {
                        "total_kcal": 1947,
                        "protein": 120,
                        "carbs": 225,
                        "fat": 63,
                        "ppk": 1.7,
                        "alloc_protein": 25,
                        "alloc_carbs": 46,
                        "alloc_fat": 29,
                    },
                    "meals": [{
                        "hour": "08:00",
                        "meal": {
                            "name": "Avena con yogur",
                            "kpis": {"total_kcal": 448, "protein": 25},
                            "foods": [
                                {"food_name": "Avena tradicional", "quantity": 70, "private": "omit"},
                                {"food_name": "Yogur natural", "quantity": 180},
                            ],
                        },
                    }],
                },
            },
        },
    }


class MCPProposalCardTests(unittest.TestCase):
    def test_projection_uses_simulated_dailyplan_without_profile_or_audit_data(self):
        card = build_proposal_card_data(proposal_detail())
        self.assertEqual(card["proposal_card"]["id"], 26)
        self.assertEqual(card["dailyplan"]["id"], 0)
        self.assertEqual(card["dailyplan"]["meals_count"], 1)
        self.assertEqual(card["dailyplan"]["foods_count"], 2)
        self.assertEqual(card["dailyplan"]["meals"][0]["foods"], [
            {"food_name": "Avena tradicional", "quantity": 70.0, "quantity_unit": "g"},
            {"food_name": "Yogur natural", "quantity": 180.0, "quantity_unit": "g"},
        ])
        self.assertNotIn("70 kg", str(card))
        self.assertNotIn("30 años", str(card))
        self.assertNotIn("private", str(card))

    def test_projection_preserves_food_units_nutrition_and_aggregation(self):
        proposal = proposal_detail()
        foods = proposal["validation_summary"]["simulation"]["dailyplan"]["meals"][0]["meal"]["foods"]
        image_path = f"/api/v1/foods/visual-assets/07ee5a6a-7dda-4951-bfc6-9c002efbe231/{'a' * 64}.png"
        foods[0].update({"food_id": 12, "unit": "g", "total_kcal": 270, "protein": 10, "carbs": 45, "fat": 5, "image_path": image_path})
        foods[1].update({"unit": "ml", "total_kcal": 120, "protein": 6, "carbs": 12, "fat": 4})
        foods.append({"food_id": 12, "food_name": "Avena tradicional", "quantity": 30, "unit": "g", "total_kcal": 115, "protein": 4, "carbs": 19, "fat": 2})

        card = build_proposal_card_data(proposal)["dailyplan"]

        self.assertEqual(card["foods_count"], 2)
        self.assertEqual(card["meals"][0]["foods"][1]["quantity_unit"], "ml")
        self.assertEqual(card["foods_aggregation"][0]["quantity"], 100.0)
        self.assertEqual(card["foods_aggregation"][0]["total_kcal"], 385.0)
        self.assertEqual(card["foods_aggregation"][0]["image_path"], image_path)
        self.assertEqual(card["meals"][0]["foods"][0]["image_path"], image_path)
        self.assertEqual(card["foods_aggregation"][1]["quantity_unit"], "ml")
        self.assertNotIn("private", str(card))

    def test_projection_rejects_nonpublic_image_path(self):
        proposal = proposal_detail()
        proposal["validation_summary"]["simulation"]["dailyplan"]["meals"][0]["meal"]["foods"][0]["image_path"] = "https://untrusted.example/food.png"
        card = build_proposal_card_data(proposal)["dailyplan"]
        self.assertNotIn("image_path", card["meals"][0]["foods"][0])
        self.assertNotIn("image_path", card["foods_aggregation"][0])

    def test_creation_summary_preserves_safe_fields_and_adds_card(self):
        result = MCPToolCallResult(ok=True, data={"proposal": proposal_detail()}, error=None)
        summary = summarize_generated_dailyplan_proposal_result(result)
        self.assertTrue(summary["ok"])
        self.assertEqual(summary["data"]["proposal_id"], 26)
        self.assertFalse(summary["data"]["applies_changes"])
        self.assertEqual(summary["data"]["dailyplan"]["name"], "Día de mantenimiento")
        self.assertNotIn("current_snapshot", str(summary))

    def test_missing_or_nonconcrete_plan_does_not_expose_raw_proposal(self):
        proposal = proposal_detail()
        proposal["validation_summary"] = {}
        result = MCPToolCallResult(ok=True, data={"proposal": proposal}, error=None)
        summary = summarize_generated_dailyplan_proposal_result(result)
        self.assertEqual(summary["data"]["proposal_id"], 26)
        self.assertNotIn("proposal_card", summary["data"])
        self.assertNotIn("70 kg", str(summary))

    def test_nonpending_proposal_and_missing_nutrition_do_not_render_card(self):
        proposal = proposal_detail()
        proposal["status"] = "applied"
        self.assertIsNone(build_proposal_card_data(proposal))
        proposal["status"] = "pending_review"
        proposal["validation_summary"]["simulation"]["dailyplan"]["kpis"] = {}
        self.assertIsNone(build_proposal_card_data(proposal))

    def test_create_tool_advertises_new_resource_and_resource_reuses_dailyplan_card(self):
        async def inspect():
            with patch.dict("os.environ", {
                "MYSCOOPE_API_BASE_URL": "http://127.0.0.1:8000/app",
                "MYSCOOPE_CARD_WEB_APP_BASE_URL": "",
            }):
                server = create_mcp_server()
                tools = {tool.name: tool for tool in await server.list_tools()}
                resource = (await server.read_resource(PROPOSAL_CARD_RESOURCE_URI))[0]
                return tools, resource

        tools, resource = asyncio.run(inspect())
        self.assertEqual(
            tools["create_nutrition_engine_dailyplan_proposal"].meta["ui"]["resourceUri"],
            PROPOSAL_CARD_RESOURCE_URI,
        )
        self.assertIn('id="proposal-shell"', resource.content)
        self.assertIn('id="nutrition-tab"', resource.content)
        self.assertIn('id="menu-tab-mobile"', resource.content)
        self.assertIn('"http://127.0.0.1:8000/app"', resource.content)
        self.assertEqual(resource.meta["openai/widgetCSP"]["redirect_domains"], ["http://127.0.0.1:8000"])
        self.assertEqual(resource.meta["openai/widgetCSP"]["resource_domains"], ["http://127.0.0.1:8000"])
