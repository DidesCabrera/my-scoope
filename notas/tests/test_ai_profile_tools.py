from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.ai_tools.profile_tools import (
    commit_profile_update_tool,
    read_user_profile_context_tool,
    share_profile_draft_card_tool,
    update_profile_draft_tool,
)
from notas.application.services.nutrition.body_metrics import record_weight
from notas.domain.models import Profile


class AIProfileToolsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="felipe", password="secret")
        profile = self.user.profile
        profile.birth_date = date(1988, 1, 17)
        profile.sex = Profile.SEX_MALE
        profile.height_cm = 188
        profile.save(update_fields=["birth_date", "sex", "height_cm"])
        record_weight(self.user, weight_kg=84, source="manual")

    def test_read_user_profile_context_returns_persisted_profile_without_writes(self):
        result = read_user_profile_context_tool(self.user)

        self.assertTrue(result.ok)
        profile_context = result.data["profile_context"]
        self.assertEqual(profile_context["height_cm"], 188)
        self.assertEqual(profile_context["sex"], Profile.SEX_MALE)
        self.assertEqual(profile_context["weight_kg"], 84)
        self.assertEqual(result.data["source_boundary"]["writes_allowed"], False)
        self.assertEqual(result.data["missing_fields"], ["activity_level"])
        draft = result.data["profile_draft"]
        self.assertEqual(draft["height_cm"], 188)
        self.assertEqual(draft["sex"], Profile.SEX_MALE)
        self.assertEqual(draft["field_sources"]["height_cm"], "profile")
        self.assertEqual(result.data["profile_draft_card"]["status"], "pending")
        self.assertEqual(result.data["nutrition_brief_patch"]["subject_source"], "self_profile")
        self.assertEqual(result.data["nutrition_brief_patch"]["ppk_weight_source"], "profile_current_weight")

    def test_update_profile_draft_normalizes_fields_without_persisting(self):
        result = update_profile_draft_tool(
            self.user,
            current_draft={"weight_kg": 84, "field_sources": {"weight_kg": "profile"}},
            updates={"height_cm": "1.88", "age_years": "38", "sex": "hombre", "activity_level": "moderate"},
        )

        self.assertTrue(result.ok)
        draft = result.data["profile_draft"]
        self.assertEqual(draft["height_cm"], 188)
        self.assertEqual(draft["age_years"], 38)
        self.assertEqual(draft["sex"], "male")
        self.assertEqual(draft["activity_level"], "moderate")
        self.assertEqual(draft["field_sources"]["height_cm"], "chat_draft")
        self.assertFalse(result.data["source_boundary"]["persistent_profile_updated"])
        self.assertTrue(result.data["source_boundary"]["persistence_requires_user_approval"])
        self.assertFalse(result.data["source_boundary"]["renderable_in_chat_thread"])
        self.assertEqual(result.data["source_boundary"]["presentation_mode"], "silent_state_update")
        self.assertEqual(result.data["source_boundary"]["share_tool"], "share_profile_draft_card")
        self.assertNotIn("profile_draft_card", result.data)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.height_cm, 188)

    def test_update_profile_draft_tolerates_number_typos_from_llm_arguments(self):
        result = update_profile_draft_tool(
            self.user,
            updates={"weight_kg": "88jg", "height_cm": "188cm", "age_years": "38 anos"},
        )

        self.assertTrue(result.ok)
        draft = result.data["profile_draft"]
        self.assertEqual(draft["weight_kg"], 88)
        self.assertEqual(draft["height_cm"], 188)
        self.assertEqual(draft["age_years"], 38)

    def test_share_profile_draft_card_returns_renderable_payload(self):
        result = share_profile_draft_card_tool(
            self.user,
            profile_draft={
                "weight_kg": 85,
                "height_cm": 188,
                "age_years": 38,
                "sex": "male",
                "activity_level": "moderate",
                "field_sources": {
                    "weight_kg": "chat_draft",
                    "height_cm": "profile",
                    "age_years": "chat_draft",
                    "sex": "profile",
                    "activity_level": "chat_draft",
                },
            },
        )

        self.assertTrue(result.ok)
        card = result.data["profile_draft_card"]
        self.assertEqual(card["status"], "complete")
        self.assertEqual(card["pending_count"], 0)
        self.assertTrue(card["has_chat_draft_updates"])
        self.assertTrue(card["can_update_personal_profile"])
        self.assertEqual(card["items"][0]["value"], "85 kg")

    def test_commit_profile_update_persists_only_approved_committable_fields(self):
        result = commit_profile_update_tool(
            self.user,
            profile_draft={
                "weight_kg": 85,
                "height_cm": 190,
                "age_years": 38,
                "sex": "male",
                "activity_level": "high",
                "field_sources": {
                    "weight_kg": "chat_draft",
                    "height_cm": "chat_draft",
                    "age_years": "chat_draft",
                    "sex": "profile",
                    "activity_level": "chat_draft",
                },
            },
        )

        self.assertTrue(result.ok)
        self.assertEqual(set(result.data["updated_fields"]), {"weight_kg", "height_cm"})
        self.assertIn("age_years", result.data["skipped_fields"])
        self.assertIn("activity_level", result.data["skipped_fields"])
        self.assertTrue(result.data["source_boundary"]["persistent_profile_updated"])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.height_cm, 190)
        self.assertEqual(self.user.profile.sex, Profile.SEX_MALE)
        self.assertEqual(self.user.weight_logs.first().weight_kg, 85)
        card = result.data["profile_draft_card"]
        height_item = next(item for item in card["items"] if item["key"] == "height_cm")
        self.assertEqual(height_item["source"], "profile")

    def test_profile_card_is_not_actionable_when_only_non_committable_chat_fields_changed(self):
        result = share_profile_draft_card_tool(
            self.user,
            profile_draft={
                "weight_kg": 84,
                "height_cm": 188,
                "age_years": 38,
                "sex": "male",
                "activity_level": "moderate",
                "field_sources": {
                    "weight_kg": "profile",
                    "height_cm": "profile",
                    "sex": "profile",
                    "age_years": "chat_draft",
                    "activity_level": "chat_draft",
                },
            },
        )

        self.assertTrue(result.ok)
        card = result.data["profile_draft_card"]
        self.assertEqual(card["status"], "complete")
        self.assertTrue(card["has_chat_draft_updates"])
        self.assertFalse(card["has_committable_profile_updates"])
        self.assertFalse(card["can_update_personal_profile"])

    def test_commit_profile_update_card_is_not_actionable_after_only_unchanged_committable_fields_remain(self):
        result = commit_profile_update_tool(
            self.user,
            profile_draft={
                "weight_kg": 84,
                "height_cm": 188,
                "age_years": 38,
                "sex": "male",
                "activity_level": "moderate",
                "field_sources": {
                    "weight_kg": "profile",
                    "height_cm": "chat_draft",
                    "age_years": "chat_draft",
                    "sex": "chat_draft",
                    "activity_level": "chat_draft",
                },
            },
        )

        self.assertTrue(result.ok)
        self.assertEqual(set(result.data["unchanged_fields"]), {"height_cm", "sex"})
        card = result.data["profile_draft_card"]
        self.assertFalse(card["has_committable_profile_updates"])
        self.assertFalse(card["can_update_personal_profile"])
        self.assertIn("age_years", result.data["skipped_fields"])
        self.assertIn("activity_level", result.data["skipped_fields"])
