from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.ai_tools.proposal_preference_tools import (
    share_proposal_preferences_card_tool,
    update_proposal_preferences_tool,
)


class AIProposalPreferenceToolsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="felipe", password="secret")

    def test_update_proposal_preferences_normalizes_proposal_scoped_fields(self):
        result = update_proposal_preferences_tool(
            self.user,
            updates={
                "goal": "aumentar de musculo",
                "requested_entity": "plan diario",
                "meals_per_day": "5",
                "energy_adjustment": "superávit leve",
                "protein_target": "180",
                "notes": "más simple, considerar gym",
            },
        )

        self.assertTrue(result.ok)
        draft = result.data["proposal_preferences"]
        self.assertEqual(draft["goal"], "muscle_gain")
        self.assertEqual(draft["requested_entity"], "daily_plan")
        self.assertEqual(draft["meals_per_day"], 5)
        self.assertEqual(draft["energy_adjustment"], "surplus_mild")
        self.assertEqual(draft["protein_target"], 180)
        self.assertEqual(draft["field_sources"]["goal"], "chat_draft")
        self.assertTrue(draft["proposal_scoped_only"])
        self.assertFalse(draft["persistent_profile_updated"])
        self.assertFalse(draft["persistent_preferences_updated"])
        self.assertEqual(result.data["nutrition_brief_patch"]["goal"], "muscle_gain")
        self.assertEqual(result.data["nutrition_brief_patch"]["meals_per_day"], 5)
        self.assertFalse(result.data["source_boundary"]["renderable_in_chat_thread"])
        self.assertEqual(result.data["source_boundary"]["presentation_mode"], "silent_state_update")
        self.assertEqual(result.data["source_boundary"]["share_tool"], "share_proposal_preferences_card")
        self.assertNotIn("proposal_preferences_card", result.data)

    def test_update_proposal_preferences_tolerates_goal_typos_from_llm_arguments(self):
        for typo in ("gamar musculos", "aumennter de muscilo", "ganra masa"):
            with self.subTest(typo=typo):
                result = update_proposal_preferences_tool(self.user, updates={"goal": typo})

                self.assertTrue(result.ok)
                self.assertEqual(result.data["proposal_preferences"]["goal"], "muscle_gain")
                self.assertEqual(result.data["nutrition_brief_patch"]["goal"], "muscle_gain")


    def test_update_proposal_preferences_normalizes_proposal_complexity(self):
        for value, expected in (("algo simple", "low"), ("intermedia", "medium"), ("más elaborada", "high")):
            with self.subTest(value=value):
                result = update_proposal_preferences_tool(
                    self.user,
                    updates={"complexity_level": value},
                )

                self.assertTrue(result.ok)
                draft = result.data["proposal_preferences"]
                self.assertEqual(draft["complexity_level"], expected)
                self.assertEqual(
                    result.data["nutrition_brief_patch"]["complexity_level"],
                    expected,
                )

    def test_share_proposal_preferences_card_returns_renderable_payload(self):
        result = share_proposal_preferences_card_tool(
            self.user,
            proposal_preferences={
                "goal": "fat_loss",
                "meals_per_day": 3,
                "calorie_target": 2100,
                "field_sources": {
                    "goal": "chat_draft",
                    "meals_per_day": "chat_draft",
                    "calorie_target": "manual",
                },
            },
        )

        self.assertTrue(result.ok)
        card = result.data["proposal_preferences_card"]
        self.assertEqual(card["status"], "has_data")
        self.assertEqual(card["known_count"], 3)
        self.assertEqual(card["sections"][0]["title"], "Dirección de la propuesta")
        target_items = card["sections"][1]["items"]
        calories = next(item for item in target_items if item["key"] == "calorie_target")
        self.assertEqual(calories["value"], "2100 kcal")
        self.assertEqual(calories["source_label"], "Manual")
