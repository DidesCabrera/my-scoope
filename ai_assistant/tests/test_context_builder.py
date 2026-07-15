from django.test import SimpleTestCase

from ai_assistant.application.chat_engines import ChatEngineRequest
from ai_assistant.application.context_builder import (
    build_safe_llm_context,
    merge_safe_context_into_request,
    sanitize_provider_context,
)
from notas.application.ai_intake.nutrition_brief import start_or_continue_conversation


class SafeLLMContextBuilderTests(SimpleTestCase):
    def test_builds_minimal_context_from_nutrition_conversation_state(self):
        request = ChatEngineRequest(
            message="Quiero un plan de 2100 kcal con 4 comidas y 160g de proteína",
            existing_payload={"raw": "session payload must not be forwarded"},
            user_id=123,
        )
        state = start_or_continue_conversation(
            message=request.normalized_message,
            existing_payload=request.existing_payload,
        )

        context = build_safe_llm_context(request, conversation_state=state).as_dict()

        self.assertEqual(context["surface"], "ai_nutrition_intake")
        self.assertEqual(context["user"], {"authenticated": True, "id_present": True})
        self.assertTrue(context["conversation"]["existing_payload_present"])
        self.assertGreaterEqual(context["conversation"]["message_count"], 2)
        self.assertNotIn("nutrition_brief", context)
        self.assertTrue(context["runtime"]["tools_enabled"])
        self.assertEqual(context["runtime"]["draft_state_scope"], "conversation")
        self.assertEqual(context["runtime"]["card_presentation"], "explicit_tool_only")
        self.assertFalse(context["runtime"]["proposal_creation_enabled"])
        self.assertTrue(context["runtime"]["persistent_writes_require_approval"])
        self.assertEqual(context["metadata"]["context_builder"], "safe_llm_context.v1")
        self.assertNotIn("conversational_intake", context["metadata"])
        proposal_preferences = context["metadata"]["tool_oriented_intake"]["current_drafts"][
            "proposal_preferences"
        ]
        self.assertEqual(proposal_preferences["calorie_target"], 2100)
        self.assertEqual(proposal_preferences["meals_per_day"], 4)

    def test_context_does_not_forward_identity_or_raw_payload_values(self):
        request = ChatEngineRequest(
            message="hola",
            existing_payload={"api_key": "secret", "email": "felipe@example.com"},
            user_id=999,
        )

        context_text = str(build_safe_llm_context(request).as_dict())

        self.assertNotIn("999", context_text)
        self.assertNotIn("secret", context_text)
        self.assertNotIn("felipe@example.com", context_text)
        self.assertIn("id_present", context_text)
        self.assertIn("existing_payload_present", context_text)

    def test_sanitizes_extra_context_and_sensitive_keys(self):
        safe = sanitize_provider_context(
            {
                "surface": "ai_assistant",
                "authorization_header": "Bearer secret-token",
                "profile_email": "felipe@example.com",
                "nested": {"csrf_token": "secret", "safe_hint": "ok"},
                "long_text": "x" * 400,
            }
        )

        self.assertEqual(safe["surface"], "ai_assistant")
        self.assertNotIn("authorization_header", safe)
        self.assertNotIn("profile_email", safe)
        self.assertNotIn("csrf_token", safe["nested"])
        self.assertEqual(safe["nested"]["safe_hint"], "ok")
        self.assertLessEqual(len(safe["long_text"]), 241)

    def test_provider_sanitizer_preserves_bounded_nested_objects(self):
        safe = sanitize_provider_context(
            {
                "metadata": {
                    "tool_oriented_intake": {
                        "current_drafts": {
                            "profile_draft": {
                                "height_cm": 188,
                                "field_sources": {"height_cm": "profile"},
                            }
                        }
                    }
                },
                "conversation": {
                    "recent_chat_objects": [
                        {
                            "type": "profile_draft_card",
                            "pending_fields": ["age_years", "sex"],
                        }
                    ]
                },
            }
        )

        profile_draft = safe["metadata"]["tool_oriented_intake"]["current_drafts"]["profile_draft"]
        self.assertEqual(profile_draft["height_cm"], 188)
        self.assertEqual(profile_draft["field_sources"]["height_cm"], "profile")
        self.assertEqual(
            safe["conversation"]["recent_chat_objects"][0]["pending_fields"],
            ["age_years", "sex"],
        )

    def test_non_intake_surface_can_keep_compact_nutrition_brief(self):
        request = ChatEngineRequest(message="resume el contexto", user_id=123)
        state = start_or_continue_conversation(
            message="quiero dieta, bajar grasa, 3 comidas",
            existing_payload=None,
        )

        context = build_safe_llm_context(
            request,
            surface="ai_assistant",
            conversation_state=state,
        ).as_dict()

        self.assertEqual(context["nutrition_brief"]["goal"], "fat_loss")
        self.assertEqual(context["nutrition_brief"]["meals_per_day"], 3)
        self.assertNotIn("known_fields", context["nutrition_brief"])
        self.assertNotIn("do_not_ask_again_fields", context["nutrition_brief"])
        self.assertNotIn("pending_field", context["nutrition_brief"])

    def test_merge_safe_context_into_request_keeps_payload_out_of_metadata(self):
        request = ChatEngineRequest(
            message="hola",
            existing_payload={"raw": "session"},
            metadata={"surface": "ai_nutrition_intake"},
        )
        safe_context = build_safe_llm_context(request)

        merged = merge_safe_context_into_request(request, safe_context=safe_context)

        self.assertEqual(merged.existing_payload, request.existing_payload)
        self.assertIn("safe_llm_context", merged.metadata)
        self.assertNotIn("raw", str(merged.metadata["safe_llm_context"]))
        self.assertEqual(merged.metadata["safe_llm_context_version"], "safe_llm_context.v1")


class ToolOrientedContextBuilderTests(SimpleTestCase):
    def test_exposes_current_drafts_without_recommended_sequence(self):
        request = ChatEngineRequest(message="quiero una dieta", user_id=123)
        state = start_or_continue_conversation(
            message="quiero dieta, bajar grasa, 3 comidas, 38 años, 188 cm, 85 kg, hombre",
            existing_payload=None,
        )

        context = build_safe_llm_context(request, conversation_state=state).as_dict()

        tool_context = context["metadata"]["tool_oriented_intake"]
        self.assertEqual(tool_context["version"], "ai_assistant_tool_oriented_intake.v9")
        self.assertEqual(tool_context["assistant_role"], "operator_assistant")
        self.assertEqual(tool_context["current_drafts"]["profile_draft"]["height_cm"], 188)
        self.assertEqual(tool_context["current_drafts"]["profile_draft"]["weight_kg"], 85.0)
        self.assertEqual(tool_context["current_drafts"]["profile_draft"]["age_years"], 38)
        self.assertEqual(tool_context["current_drafts"]["profile_draft"]["sex"], "male")
        self.assertEqual(tool_context["current_drafts"]["proposal_preferences"]["goal"], "fat_loss")
        self.assertEqual(tool_context["current_drafts"]["proposal_preferences"]["meals_per_day"], 3)
        self.assertNotIn("recommended_tool_sequence", tool_context)
        self.assertNotIn("rules", tool_context)

    def test_tool_context_omits_completeness_and_do_not_ask_policies(self):
        request = ChatEngineRequest(message="Completemoslos", user_id=123)
        state = start_or_continue_conversation(
            message="quiero dieta para ganar masa, usemos mi ficha, 84 kg, 188 cm",
            existing_payload=None,
        )

        context = build_safe_llm_context(request, conversation_state=state).as_dict()
        tool_context = context["metadata"]["tool_oriented_intake"]
        serialized_context = str(context)

        self.assertNotIn("legacy_follow_up_questions_omitted", context["conversation"])
        self.assertNotIn("visible_follow_up_questions", context["conversation"])
        self.assertNotIn("profile_completion", tool_context)
        self.assertNotIn("do_not_ask_again_fields", serialized_context)
        self.assertNotIn("recommended_tool_sequence", serialized_context)
        self.assertTrue(
            tool_context["context_semantics"]["present_values_are_known_for_this_conversation"]
        )
        self.assertTrue(
            tool_context["context_semantics"]["absent_values_are_not_automatically_required"]
        )

    def test_context_exposes_recent_profile_card_state_without_instructions(self):
        request = ChatEngineRequest(message="Completemoslos", user_id=123)
        state = start_or_continue_conversation(
            message="quiero dieta para ganar masa, usemos mi ficha, 84 kg, 188 cm",
            existing_payload=None,
        )

        context = build_safe_llm_context(request, conversation_state=state).as_dict()

        chat_objects = context["conversation"]["recent_chat_objects"]
        self.assertTrue(chat_objects)
        last_object = context["conversation"]["last_shared_object"]
        self.assertEqual(last_object["type"], "profile_draft_card")
        self.assertEqual(last_object["pending_count"], 3)
        self.assertIn("age_years", last_object["pending_fields"])
        self.assertIn("sex", last_object["pending_fields"])
        self.assertIn("activity_level", last_object["pending_fields"])
        self.assertIn("height_cm", last_object["known_fields"])
        self.assertNotIn("instructional_meaning", last_object)

    def test_tool_context_treats_weight_source_as_internal_metadata(self):
        request = ChatEngineRequest(message="quiero seguir", user_id=123)
        state = start_or_continue_conversation(
            message="quiero dieta, bajar grasa, peso 85 kg, 188 cm, 38 años, hombre",
            existing_payload=None,
        )

        context = build_safe_llm_context(request, conversation_state=state).as_dict()
        context_text = str(context)
        tool_context = context["metadata"]["tool_oriented_intake"]

        self.assertEqual(tool_context["version"], "ai_assistant_tool_oriented_intake.v9")
        self.assertEqual(tool_context["current_drafts"]["profile_draft"]["weight_kg"], 85.0)
        self.assertNotIn("nutrition_brief", context)
        self.assertNotIn("ppk_weight_source", context_text)
        self.assertNotIn("weight_source", context_text)

    def test_reviewable_proposal_runtime_flag_follows_settings(self):
        request = ChatEngineRequest(message="quiero una dieta", user_id=123)

        with self.settings(AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS=True):
            context = build_safe_llm_context(request).as_dict()

        self.assertTrue(context["runtime"]["proposal_creation_enabled"])
        self.assertNotIn("reviewable_proposal_tools_enabled", context["runtime"])
        self.assertTrue(context["runtime"]["persistent_writes_require_approval"])
