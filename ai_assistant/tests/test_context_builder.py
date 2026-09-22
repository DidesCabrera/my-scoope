from django.test import SimpleTestCase

from ai_assistant.application.chat_engines import ChatEngineRequest
from ai_assistant.application.context_builder import (
    build_safe_llm_context,
    merge_safe_context_into_request,
    sanitize_provider_context,
)
from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    NutritionConversationMessage,
    NutritionConversationState,
    build_llm_intake_result_from_brief,
    start_or_continue_conversation,
)


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
        self.assertEqual(context["runtime"]["card_presentation"], "automatic_from_tool_results")
        self.assertTrue(context["runtime"]["proposal_creation_enabled"])
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

    def test_provider_sanitizer_does_not_retruncate_executor_bounded_collections(self):
        foods = [{"id": index, "name": f"Food {index}"} for index in range(13)]

        safe = sanitize_provider_context(
            {
                "data": {
                    "resource": "foods",
                    "scope": "library",
                    "foods": foods,
                    "total_count": 13,
                    "returned_count": 13,
                    "has_more": False,
                }
            }
        )

        self.assertEqual(len(safe["data"]["foods"]), 13)
        self.assertEqual(safe["data"]["total_count"], 13)
        self.assertEqual(safe["data"]["returned_count"], 13)
        self.assertFalse(safe["data"]["has_more"])

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
    def _state_with_messages(self, *messages):
        return NutritionConversationState(
            messages=list(messages),
            result=build_llm_intake_result_from_brief(NutritionBrief(raw_prompt="")),
        )

    def test_exposes_current_drafts_without_recommended_sequence(self):
        request = ChatEngineRequest(message="quiero una dieta", user_id=123)
        state = start_or_continue_conversation(
            message="quiero dieta, bajar grasa, 3 comidas, 38 años, 188 cm, 85 kg, hombre",
            existing_payload=None,
        )

        context = build_safe_llm_context(request, conversation_state=state).as_dict()

        tool_context = context["metadata"]["tool_oriented_intake"]
        self.assertEqual(tool_context["version"], "ai_assistant_workspace.v2")
        self.assertEqual(
            tool_context["client_memory_contract"],
            "ai_assistant_client_memory.v2",
        )
        self.assertEqual(tool_context["assistant_role"], "collaborative_product_assistant")
        self.assertEqual(tool_context["current_drafts"]["profile_draft"]["height_cm"], 188)
        self.assertEqual(tool_context["current_drafts"]["profile_draft"]["weight_kg"], 85.0)
        self.assertEqual(tool_context["current_drafts"]["profile_draft"]["age_years"], 38)
        self.assertEqual(tool_context["current_drafts"]["profile_draft"]["sex"], "male")
        self.assertEqual(tool_context["current_drafts"]["proposal_preferences"]["goal"], "fat_loss")
        self.assertEqual(tool_context["current_drafts"]["proposal_preferences"]["meals_per_day"], 3)
        self.assertNotIn("recommended_tool_sequence", tool_context)
        self.assertNotIn("rules", tool_context)

    def test_common_nutrition_goal_becomes_an_outcome_not_an_endless_intake(self):
        request = ChatEngineRequest(message="Quiero perder grasa", user_id=123)
        state = start_or_continue_conversation(
            message=request.normalized_message,
            existing_payload=None,
        )

        context = build_safe_llm_context(request, conversation_state=state).as_dict()
        progress = context["metadata"]["tool_oriented_intake"]["work_progress"]

        self.assertEqual(
            progress["active_objective"],
            "create_reviewable_dailyplan_proposal",
        )
        self.assertEqual(progress["active_work"]["resource"], "dailyplan")
        self.assertEqual(
            progress["active_work"]["expected_outcome"],
            "nutrition_proposal",
        )
        self.assertFalse(
            progress["active_work"]["inference_grants_write_authority"]
        )

    def test_latest_explicit_program_request_replaces_an_older_plan_objective(self):
        state = self._state_with_messages(
            NutritionConversationMessage(role="user", text="Quiero un plan diario"),
            NutritionConversationMessage(role="assistant", text="De acuerdo."),
            NutritionConversationMessage(
                role="user",
                text="Mejor hagamos un programa semanal.",
            ),
        )
        context = build_safe_llm_context(
            ChatEngineRequest(message="Mejor hagamos un programa semanal.", user_id=123),
            conversation_state=state,
        ).as_dict()

        active_work = context["metadata"]["tool_oriented_intake"]["work_progress"][
            "active_work"
        ]
        self.assertEqual(active_work["objective"], "prepare_reviewable_workspace_patch")
        self.assertEqual(active_work["expected_outcome"], "prepared_patch")
        self.assertEqual(active_work["resource"], "program")
        self.assertEqual(active_work["source"], "current_message")

    def test_nutrition_direction_change_advances_the_conversation_draft(self):
        message = "Mejor hagamos un programa semanal para bajar grasa."
        state = self._state_with_messages(
            NutritionConversationMessage(
                role="user",
                text="Quiero un plan diario para ganar masa muscular.",
            ),
            NutritionConversationMessage(role="assistant", text="De acuerdo."),
            NutritionConversationMessage(role="user", text=message),
        )
        context = build_safe_llm_context(
            ChatEngineRequest(message=message, user_id=123),
            conversation_state=state,
        ).as_dict()

        active_work = context["metadata"]["tool_oriented_intake"]["work_progress"][
            "active_work"
        ]
        self.assertEqual(active_work["objective"], "record_conversation_facts")
        self.assertEqual(active_work["expected_outcome"], "workspace_advanced")
        self.assertEqual(active_work["resource"], "program")
        self.assertEqual(active_work["action"], "update_draft")

    def test_meal_request_wins_over_later_plan_context_reference(self):
        message = (
            "Crea ahora una propuesta revisable de comida de 450 kcal usando el "
            "plan diario de contexto ID 2."
        )
        state = self._state_with_messages(
            NutritionConversationMessage(role="user", text=message)
        )
        context = build_safe_llm_context(
            ChatEngineRequest(message=message, user_id=123),
            conversation_state=state,
        ).as_dict()

        active_work = context["metadata"]["tool_oriented_intake"]["work_progress"][
            "active_work"
        ]
        self.assertEqual(
            active_work["objective"],
            "create_reviewable_meal_proposal",
        )
        self.assertEqual(active_work["expected_outcome"], "nutrition_proposal")
        self.assertEqual(active_work["resource"], "meal")

    def test_creation_guardrail_is_not_misread_as_mutation_authority(self):
        message = (
            "Crea un plan diario de 2400 kcal con distribución 30/50/20 y cuatro "
            "comidas. No apliques la propuesta sin mi aprobación."
        )
        state = self._state_with_messages(
            NutritionConversationMessage(role="user", text=message)
        )
        context = build_safe_llm_context(
            ChatEngineRequest(message=message, user_id=123),
            conversation_state=state,
        ).as_dict()

        active_work = context["metadata"]["tool_oriented_intake"]["work_progress"][
            "active_work"
        ]
        self.assertEqual(
            active_work["objective"],
            "create_reviewable_dailyplan_proposal",
        )
        self.assertEqual(active_work["expected_outcome"], "nutrition_proposal")
        self.assertEqual(active_work["resource"], "dailyplan")

    def test_short_continuation_retains_previous_reviewable_change_objective(self):
        state = self._state_with_messages(
            NutritionConversationMessage(
                role="user",
                text="Renombra mi comida a Almuerzo rápido.",
            ),
            NutritionConversationMessage(role="assistant", text="Puedo prepararlo."),
            NutritionConversationMessage(role="user", text="Hazlo."),
        )
        context = build_safe_llm_context(
            ChatEngineRequest(message="Hazlo.", user_id=123),
            conversation_state=state,
        ).as_dict()

        active_work = context["metadata"]["tool_oriented_intake"]["work_progress"][
            "active_work"
        ]
        self.assertEqual(active_work["objective"], "prepare_reviewable_workspace_patch")
        self.assertEqual(active_work["resource"], "meal")
        self.assertEqual(active_work["action"], "rename")
        self.assertEqual(active_work["source"], "conversation_history")

    def test_workspace_question_becomes_a_query_outcome(self):
        state = self._state_with_messages(
            NutritionConversationMessage(
                role="user",
                text="¿Qué programas tengo activos?",
            )
        )
        context = build_safe_llm_context(
            ChatEngineRequest(message="¿Qué programas tengo activos?", user_id=123),
            conversation_state=state,
        ).as_dict()

        active_work = context["metadata"]["tool_oriented_intake"]["work_progress"][
            "active_work"
        ]
        self.assertEqual(active_work["objective"], "query_workspace")
        self.assertEqual(active_work["expected_outcome"], "workspace_query")
        self.assertEqual(active_work["resource"], "program")

    def test_review_artifact_closes_an_older_objective(self):
        state = self._state_with_messages(
            NutritionConversationMessage(role="user", text="Crea un plan diario"),
            NutritionConversationMessage(
                role="assistant",
                text="",
                proposal_review_card={"id": "proposal-1"},
            ),
            NutritionConversationMessage(role="user", text="Gracias"),
        )
        context = build_safe_llm_context(
            ChatEngineRequest(message="Gracias", user_id=123),
            conversation_state=state,
        ).as_dict()

        active_work = context["metadata"]["tool_oriented_intake"]["work_progress"][
            "active_work"
        ]
        self.assertEqual(active_work["status"], "response_only")
        self.assertEqual(active_work["objective"], "respond_to_current_message")

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

        self.assertEqual(tool_context["version"], "ai_assistant_workspace.v2")
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

    def test_preference_workspace_uses_the_same_canonical_fields_as_tools(self):
        request = ChatEngineRequest(message="quiero algo simple", user_id=123)
        state = start_or_continue_conversation(
            message="quiero una dieta simple, presupuesto bajo, con 3 comidas y sin atún",
            existing_payload=None,
        )

        context = build_safe_llm_context(request, conversation_state=state).as_dict()
        preference_draft = context["metadata"]["tool_oriented_intake"]["current_drafts"]["preference_draft"]

        self.assertNotIn("excluded_foods", preference_draft)
        self.assertNotIn("budget_level", preference_draft)
        self.assertNotIn("meals_per_day", preference_draft)
        self.assertEqual(preference_draft.get("preferred_meals_per_day"), 3)
        self.assertEqual(preference_draft.get("budget_preference"), "low")
        self.assertEqual(preference_draft.get("simplicity_preference"), "high")
