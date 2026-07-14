from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.ai_tools.preference_tools import (
    share_preference_draft_card_tool,
    update_preference_draft_tool,
)


class AIPreferenceToolsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="felipe", password="secret")

    def test_update_preference_draft_normalizes_food_and_meal_preferences_without_persisting(self):
        result = update_preference_draft_tool(
            self.user,
            updates={
                "dietary_pattern": "vegano",
                "avoided_foods": ["atun", "lácteos", "atun"],
                "preferred_foods": "pollo, arroz, huevos",
                "preferred_meals_per_day": "5",
                "budget_preference": "bajo",
                "simplicity_preference": "alta",
            },
        )

        self.assertTrue(result.ok)
        draft = result.data["preference_draft"]
        self.assertEqual(draft["dietary_pattern"], "vegan")
        self.assertEqual(draft["avoided_foods"], ["atun", "lácteos"])
        self.assertEqual(draft["preferred_foods"], ["pollo", "arroz", "huevos"])
        self.assertEqual(draft["preferred_meals_per_day"], 5)
        self.assertEqual(draft["budget_preference"], "low")
        self.assertEqual(draft["simplicity_preference"], "high")
        self.assertEqual(draft["field_sources"]["dietary_pattern"], "chat_draft")
        self.assertFalse(result.data["source_boundary"]["writes_allowed"])
        self.assertFalse(result.data["source_boundary"]["persistent_preferences_updated"])
        self.assertFalse(result.data["source_boundary"]["renderable_in_chat_thread"])
        self.assertEqual(result.data["source_boundary"]["presentation_mode"], "silent_state_update")
        self.assertEqual(result.data["source_boundary"]["share_tool"], "share_preference_draft_card")
        self.assertTrue(result.data["source_boundary"]["persistence_requires_user_approval"])
        self.assertNotIn("preference_draft_card", result.data)

    def test_share_preference_draft_card_returns_renderable_payload(self):
        result = share_preference_draft_card_tool(
            self.user,
            preference_draft={
                "preferred_foods": ["pollo", "arroz"],
                "avoided_foods": ["pescado"],
                "preferred_meals_per_day": 3,
                "field_sources": {
                    "preferred_foods": "chat_draft",
                    "avoided_foods": "chat_draft",
                    "preferred_meals_per_day": "chat_draft",
                },
            },
        )

        self.assertTrue(result.ok)
        card = result.data["preference_draft_card"]
        self.assertEqual(card["title"], "Preferencias para esta propuesta")
        self.assertEqual(card["known_count"], 3)
        self.assertTrue(card["has_chat_draft_updates"])
        self.assertFalse(card["can_update_preferences"])
        food_items = card["sections"][0]["items"]
        preferred_item = next(item for item in food_items if item["key"] == "preferred_foods")
        self.assertEqual(preferred_item["value"], "pollo, arroz")
