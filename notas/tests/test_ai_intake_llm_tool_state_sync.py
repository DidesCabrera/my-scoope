from django.test import SimpleTestCase

from notas.application.ai_intake.chat_engine import _apply_llm_tool_results_to_conversation_state
from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    NutritionConversationMessage,
    NutritionConversationState,
    build_intake_result_from_brief,
    deserialize_brief,
    serialize_brief,
)


class AiIntakeLLMToolStateSyncTests(SimpleTestCase):
    def _conversation(self, brief=None):
        brief = brief or NutritionBrief(raw_prompt="quiero una dieta")
        return NutritionConversationState(
            messages=[
                NutritionConversationMessage(role="user", text="quiero una dieta"),
                NutritionConversationMessage(role="assistant", text="Cuéntame qué necesitas."),
            ],
            result=build_intake_result_from_brief(brief),
        )

    def test_profile_draft_tool_result_updates_legacy_conversation_brief(self):
        conversation = self._conversation(NutritionBrief(raw_prompt="quiero una dieta", goal="muscle_gain"))
        metadata = {
            "tool_results": [
                {
                    "tool_name": "update_profile_draft",
                    "status": "ok",
                    "data": {
                        "profile_draft": {
                            "weight_kg": 85.0,
                            "height_cm": 188,
                            "age_years": 38,
                            "sex": "male",
                            "activity_level": "moderate",
                            "field_sources": {
                                "weight_kg": "chat_draft",
                                "height_cm": "chat_draft",
                                "age_years": "chat_draft",
                                "sex": "chat_draft",
                                "activity_level": "chat_draft",
                            },
                        }
                    },
                }
            ]
        }

        updated, applied = _apply_llm_tool_results_to_conversation_state(conversation, metadata)
        brief = updated.result.brief

        self.assertEqual(applied, 1)
        self.assertEqual(brief.weight_kg, 85.0)
        self.assertEqual(brief.height_cm, 188)
        self.assertEqual(brief.age_years, 38)
        self.assertEqual(brief.sex, "male")
        self.assertEqual(brief.activity_level, "moderate")
        self.assertEqual(brief.field_sources["height_cm"], "chat_draft")
        self.assertNotIn("height_cm", updated.required_follow_up_questions)

    def test_proposal_preferences_tool_result_updates_goal_and_meals(self):
        conversation = self._conversation()
        metadata = {
            "tool_results": [
                {
                    "tool_name": "update_proposal_preferences",
                    "status": "ok",
                    "data": {
                        "proposal_preferences": {
                            "goal": "fat_loss",
                            "meals_per_day": 3,
                            "energy_adjustment": "deficit_mild",
                            "complexity_level": "low",
                            "notes": ["El usuario prefiere una propuesta sencilla."],
                            "field_sources": {
                                "goal": "chat_draft",
                                "meals_per_day": "manual",
                                "energy_adjustment": "chat_draft",
                                "complexity_level": "chat_draft",
                                "notes": "chat_draft",
                            },
                        },
                        "nutrition_brief_patch": {
                            "goal": "fat_loss",
                            "meals_per_day": 3,
                            "energy_adjustment": "deficit_mild",
                            "complexity_level": "low",
                        },
                    },
                }
            ]
        }

        updated, applied = _apply_llm_tool_results_to_conversation_state(conversation, metadata)
        brief = updated.result.brief

        self.assertEqual(applied, 1)
        self.assertEqual(brief.goal, "fat_loss")
        self.assertEqual(brief.meals_per_day, 3)
        self.assertEqual(brief.energy_adjustment, "deficit_mild")
        self.assertEqual(brief.complexity_level, "low")
        self.assertEqual(brief.field_sources["goal"], "chat_draft")
        self.assertEqual(brief.field_sources["meals_per_day"], "manual")
        self.assertEqual(brief.field_sources["energy_adjustment"], "chat_draft")
        self.assertEqual(brief.field_sources["complexity_level"], "chat_draft")

    def test_preference_draft_tool_result_updates_food_preferences_without_profile_fields(self):
        conversation = self._conversation(NutritionBrief(raw_prompt="quiero una dieta", preferred_foods=["pollo"]))
        metadata = {
            "tool_results": [
                {
                    "tool_name": "update_preference_draft",
                    "status": "ok",
                    "data": {
                        "preference_draft": {
                            "avoided_foods": ["atún"],
                            "preferred_foods": ["huevos", "pollo"],
                            "dietary_pattern": "omnivore",
                            "preferred_meals_per_day": 4,
                            "simplicity_preference": "high",
                            "field_sources": {
                                "avoided_foods": "chat_draft",
                                "preferred_foods": "manual",
                                "dietary_pattern": "chat_draft",
                                "preferred_meals_per_day": "chat_draft",
                                "simplicity_preference": "chat_draft",
                            },
                        }
                    },
                }
            ]
        }

        updated, applied = _apply_llm_tool_results_to_conversation_state(conversation, metadata)
        brief = updated.result.brief

        self.assertEqual(applied, 1)
        self.assertEqual(brief.excluded_foods, ["atún"])
        self.assertEqual(brief.preferred_foods, ["pollo", "huevos"])
        self.assertEqual(brief.meals_per_day, 4)
        self.assertIn("simple", brief.style_preferences)
        self.assertEqual(brief.complexity_level, "low")
        self.assertTrue(any("Patrón alimentario" in note for note in brief.notes))
        self.assertEqual(brief.field_sources["excluded_foods"], "chat_draft")
        self.assertEqual(brief.field_sources["preferred_foods"], "manual")
        self.assertEqual(brief.field_sources["meals_per_day"], "chat_draft")
        self.assertEqual(brief.field_sources["style_preferences"], "chat_draft")
        self.assertEqual(brief.field_sources["complexity_level"], "chat_draft")
        self.assertEqual(brief.field_sources["notes"], "chat_draft")

    def test_read_profile_context_tool_result_records_profile_source_and_profile_fields(self):
        conversation = self._conversation(NutritionBrief(raw_prompt="quiero una dieta", goal="fat_loss"))
        metadata = {
            "tool_results": [
                {
                    "tool_name": "read_user_profile_context",
                    "status": "ok",
                    "data": {
                        "profile_context": {
                            "weight_kg": 84.0,
                            "height_cm": 188,
                            "age_years": 38,
                            "sex": "male",
                        },
                        "profile_draft": {
                            "weight_kg": 84.0,
                            "height_cm": 188,
                            "age_years": 38,
                            "sex": "male",
                            "field_sources": {
                                "weight_kg": "profile",
                                "height_cm": "profile",
                                "age_years": "profile",
                                "sex": "profile",
                            },
                        },
                        "nutrition_brief_patch": {
                            "subject_source": "self_profile",
                            "ppk_weight_source": "profile_current_weight",
                        },
                    },
                }
            ]
        }

        updated, applied = _apply_llm_tool_results_to_conversation_state(conversation, metadata)
        brief = updated.result.brief

        self.assertEqual(applied, 1)
        self.assertEqual(brief.subject_source, "self_profile")
        self.assertEqual(brief.ppk_weight_source, "profile_current_weight")
        self.assertEqual(brief.weight_kg, 84.0)
        self.assertEqual(brief.height_cm, 188)
        self.assertEqual(brief.age_years, 38)
        self.assertEqual(brief.sex, "male")
        self.assertEqual(brief.field_sources["height_cm"], "profile")
        self.assertNotIn("subject_source", updated.required_follow_up_questions)

    def test_chat_weight_draft_marks_weight_as_manual_current_for_proposal(self):
        conversation = self._conversation(NutritionBrief(raw_prompt="quiero una dieta"))
        metadata = {
            "tool_results": [
                {
                    "tool_name": "update_profile_draft",
                    "status": "ok",
                    "data": {
                        "profile_draft": {
                            "weight_kg": 85.0,
                            "field_sources": {"weight_kg": "chat_draft"},
                        }
                    },
                }
            ]
        }

        updated, applied = _apply_llm_tool_results_to_conversation_state(conversation, metadata)
        brief = updated.result.brief

        self.assertEqual(applied, 1)
        self.assertEqual(brief.weight_kg, 85.0)
        self.assertEqual(brief.ppk_weight_source, "manual_subject_weight")
        self.assertEqual(brief.field_sources["weight_kg"], "chat_draft")

    def test_field_sources_round_trip_preserves_profile_proposal_and_preference_provenance(self):
        brief = NutritionBrief(
            raw_prompt="quiero una dieta",
            goal="muscle_gain",
            meals_per_day=3,
            height_cm=188,
            excluded_foods=["atún"],
            field_sources={
                "goal": "chat_draft",
                "meals_per_day": "manual",
                "height_cm": "profile",
                "excluded_foods": "chat_draft",
            },
        )

        restored = deserialize_brief(serialize_brief(brief))

        self.assertIsNotNone(restored)
        self.assertEqual(
            restored.field_sources,
            {
                "goal": "chat_draft",
                "meals_per_day": "manual",
                "height_cm": "profile",
                "excluded_foods": "chat_draft",
            },
        )
