from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.ai_intake.nutrition_brief import serialize_brief
from notas.application.ai_tools.proposal_tools import (
    build_nutrition_brief_from_ai_drafts,
    create_nutrition_engine_dailyplan_proposal_from_drafts_tool,
)
from notas.application.dto.nutrition_subject_context_dto import SUBJECT_SOURCE_MANUAL_CHAT_DATA
from notas.domain.models import NutritionProposal


class AIProposalFromDraftToolsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="felipe", password="secret")

    def test_builds_nutrition_brief_from_profile_preferences_and_proposal_drafts(self):
        brief = build_nutrition_brief_from_ai_drafts(
            profile_draft={
                "weight_kg": 85,
                "height_cm": 188,
                "age_years": 38,
                "sex": "male",
                "activity_level": "moderate",
                "training_frequency": 3,
                "field_sources": {
                    "weight_kg": "chat_draft",
                    "height_cm": "chat_draft",
                    "age_years": "chat_draft",
                    "sex": "chat_draft",
                    "activity_level": "chat_draft",
                },
            },
            preference_draft={
                "avoided_foods": ["atún"],
                "preferred_foods": ["pollo", "huevos"],
                "dietary_pattern": "omnivore",
                "simplicity_preference": True,
                "budget_preference": "low",
            },
            proposal_preferences={
                "goal": "muscle_gain",
                "meals_per_day": 4,
                "energy_adjustment": "surplus_mild",
                "protein_per_kg_target": 2.0,
                "macro_distribution": {"protein": 30, "carbs": 50, "fat": 20},
            },
            raw_prompt="Quiero ganar masa muscular.",
        )

        self.assertEqual(brief.subject_source, SUBJECT_SOURCE_MANUAL_CHAT_DATA)
        self.assertEqual(brief.goal, "muscle_gain")
        self.assertEqual(brief.meals_per_day, 4)
        self.assertEqual(brief.weight_kg, 85)
        self.assertEqual(brief.height_cm, 188)
        self.assertEqual(brief.age_years, 38)
        self.assertEqual(brief.sex, "male")
        self.assertEqual(brief.activity_level, "moderate")
        self.assertEqual(brief.training_frequency, 3)
        self.assertEqual(brief.energy_adjustment, "surplus_mild")
        self.assertEqual(brief.protein_per_kg_target, 2.0)
        self.assertEqual(
            brief.macro_distribution,
            {"protein": 30, "carbs": 50, "fat": 20},
        )
        serialized = serialize_brief(brief)
        self.assertEqual(serialized["protein_per_kg_target"], 2.0)
        self.assertEqual(serialized["macro_distribution"]["carbs"], 50)
        self.assertIn("atún", brief.excluded_foods)
        self.assertIn("pollo", brief.preferred_foods)
        self.assertIn("simple", brief.style_preferences)
        self.assertEqual(brief.budget_level, "low")
        self.assertTrue(brief.is_ready_for_proposal)
        self.assertEqual(brief.field_sources["height_cm"], "chat_draft")

    def test_create_dailyplan_proposal_from_drafts_delegates_to_nutrition_engine(self):
        with patch(
            "notas.application.ai_tools.proposal_tools._create_nutrition_engine_dailyplan_proposal_data"
        ) as create_from_brief:
            create_from_brief.return_value = {
                "proposal": {"id": 301, "status": "pending_review", "proposal_type": "dailyplan"},
                "source_proposal": {"id": 300},
            }

            result = create_nutrition_engine_dailyplan_proposal_from_drafts_tool(
                self.user,
                profile_draft={
                    "weight_kg": 85,
                    "height_cm": 188,
                    "age_years": 38,
                    "sex": "male",
                    "activity_level": "moderate",
                },
                proposal_preferences={"goal": "fat_loss", "meals_per_day": 3},
                preference_draft={"avoided_foods": ["pescado"], "simplicity_preference": True},
                raw_prompt="Quiero bajar grasa.",
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.data["proposal"]["id"], 301)
        self.assertTrue(result.data["draft_sources"]["profile_draft_used"])
        self.assertFalse(result.data["source_boundary"]["applies_changes"])
        called_brief = create_from_brief.call_args.kwargs["nutrition_brief"]
        self.assertEqual(called_brief["goal"], "fat_loss")
        self.assertEqual(called_brief["meals_per_day"], 3)
        self.assertEqual(called_brief["height_cm"], 188)
        self.assertIn("pescado", called_brief["excluded_foods"])

    def test_explicit_calorie_and_macros_create_without_inventing_a_goal(self):
        with patch(
            "notas.application.ai_tools.proposal_tools._create_nutrition_engine_dailyplan_proposal_data"
        ) as create_from_brief:
            create_from_brief.return_value = {
                "proposal": {"id": 401, "status": "pending_review", "proposal_type": "dailyplan"},
                "source_proposal": {"id": 400},
            }

            result = create_nutrition_engine_dailyplan_proposal_from_drafts_tool(
                self.user,
                profile_draft={},
                proposal_preferences={
                    "requested_entity": "daily_plan",
                    "meals_per_day": 4,
                    "calorie_target": 2400,
                    "protein_target": 180,
                    "carb_target": 300,
                    "fat_target": 53.33,
                    "macro_distribution": {"protein": 30, "carbs": 50, "fat": 20},
                },
                raw_prompt="Crea un plan de 2400 kcal con 30/50/20.",
            )

        self.assertTrue(result.ok)
        called_brief = create_from_brief.call_args.kwargs["nutrition_brief"]
        self.assertIsNone(called_brief["goal"])
        self.assertEqual(called_brief["calorie_target"], 2400)
        self.assertEqual(called_brief["macro_distribution"]["carbs"], 50)

    def test_create_dailyplan_proposal_from_drafts_blocks_when_minimum_brief_is_incomplete(self):
        result = create_nutrition_engine_dailyplan_proposal_from_drafts_tool(
            self.user,
            profile_draft={"weight_kg": 85},
            proposal_preferences={"goal": "muscle_gain"},
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "nutrition_brief_has_pending_questions")

    def test_failed_generation_rolls_back_source_brief_proposal(self):
        result = create_nutrition_engine_dailyplan_proposal_from_drafts_tool(
            self.user,
            profile_draft={
                "weight_kg": 80,
                "height_cm": 180,
                "age_years": 38,
                "sex": "male",
                "activity_level": "high",
                "training_frequency": 4,
            },
            proposal_preferences={
                "goal": "muscle_gain",
                "requested_entity": "daily_plan",
                "meals_per_day": 4,
                "calorie_target": 2400,
                "protein_target": 150,
                "carb_target": 300,
                "fat_target": 53,
                "macro_distribution": {"protein": 30, "carbs": 50, "fat": 20},
            },
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "nutrition_target_macro_modes_conflict")
        self.assertEqual(NutritionProposal.objects.filter(created_by=self.user).count(), 0)
