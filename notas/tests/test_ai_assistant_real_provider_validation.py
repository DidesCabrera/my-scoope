from __future__ import annotations

from dataclasses import replace
from datetime import date
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from ai_assistant.application.chat_engines import ChatEngineTurnResult
from ai_assistant.models import AIUsageEvent
from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    NutritionConversationMessage,
    NutritionConversationState,
    build_llm_intake_result_from_brief,
    deserialize_conversation,
)
from notas.application.ai_intake.real_provider_validation import (
    RealProviderValidationScenario,
    RealProviderValidationTurn,
    _behavioral_surface_check,
    _expected_brief_check,
    _known_facts_not_reasked_check,
    _response_repetition_check,
    _specialize_scenario_for_user,
    built_in_real_provider_scenarios,
    _post_tool_fallback_pacing_check,
    _provider_followup_health_check,
    _structured_provider_contract_check,
    _tool_result_grounding_check,
    get_validation_user,
    run_real_provider_validation,
)
from notas.application.services.nutrition.body_metrics import (
    calculate_age_years,
    record_weight,
)
from notas.domain.models import Profile


class ScriptedGroupedFactsValidationEngine:
    engine_name = "scripted_cm24_engine"

    def continue_chat(self, request):
        existing = deserialize_conversation(request.existing_payload)
        if existing:
            brief = existing.result.brief
            messages = list(existing.messages)
        else:
            brief = NutritionBrief(raw_prompt=request.normalized_message)
            messages = []

        messages.append(NutritionConversationMessage(role="user", text=request.normalized_message))
        if "muéstrame" in request.normalized_message.lower():
            assistant = "Claro. Te muestro las preferencias que usaré."
            messages.extend(
                [
                    NutritionConversationMessage(role="assistant", text=assistant),
                    NutritionConversationMessage(role="assistant", text="", preference_draft_card={"title": "Preferencias"}),
                    NutritionConversationMessage(
                        role="assistant",
                        text="",
                        proposal_preferences_card={"title": "Propuesta"},
                    ),
                ]
            )
            tool_results = [
                {"tool_name": "share_preference_draft_card", "status": "ok"},
                {"tool_name": "share_proposal_preferences_card", "status": "ok"},
            ]
            missing_slots = []
        else:
            brief = replace(
                brief,
                goal="muscle_gain",
                requested_entity="daily_plan",
                subject_source="self_profile",
                weight_kg=85.0,
                height_cm=188,
                age_years=38,
                sex="male",
                activity_level="high",
                training_frequency=3,
                meals_per_day=4,
                complexity_level="low",
            )
            assistant = "Perfecto. Registré los datos que entregaste juntos."
            messages.extend(
                [
                    NutritionConversationMessage(role="assistant", text=assistant),
                    NutritionConversationMessage(role="assistant", text="", profile_draft_card={"title": "Ficha"}),
                ]
            )
            tool_results = [
                {"tool_name": "read_user_profile_context", "status": "ok"},
                {"tool_name": "update_profile_draft", "status": "ok"},
                {"tool_name": "update_proposal_preferences", "status": "ok"},
            ]
            missing_slots = []

        AIUsageEvent.objects.create(
            user=request.metadata["tool_user"],
            period="2026-07",
            conversation_id=request.metadata["conversation_id"],
            turn_id=request.metadata["turn_id"],
            action_type=request.metadata["action_type"],
            provider="openai",
            model_name="test-real-model",
            input_tokens=100,
            output_tokens=20,
            total_tokens=120,
            status=AIUsageEvent.Status.COMPLETED,
            tool_calls_count=len(tool_results),
        )
        state = NutritionConversationState(
            messages=messages,
            result=build_llm_intake_result_from_brief(brief),
        )
        return ChatEngineTurnResult(
            state=state,
            assistant_text=assistant,
            is_ready_for_proposal=state.is_ready_for_proposal,
            engine_name=self.engine_name,
            metadata={
                "llm_semantic_intent": "capture_nutrition_brief",
                "llm_semantic_missing_slots": missing_slots,
                "llm_tool_results": tool_results,
                "llm_provider_native_tool_transport": bool(tool_results),
                "llm_provider_native_tool_calls": len(tool_results),
                "llm_preview_fallback": False,
                "deterministic_runtime_invoked": False,
            },
        )


@override_settings(
    AI_ASSISTANT_LLM_PROVIDER="openai",
    AI_ASSISTANT_OPENAI_MODEL="test-real-model",
    AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED=True,
    AI_ASSISTANT_CREDITS_ENABLED=False,
)
class RealProviderValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="cm24-user",
            email="cm24@example.com",
            password="not-used",
        )

    def test_grouped_facts_scenario_passes_hard_invariants_with_safe_metadata(self):
        report = run_real_provider_validation(
            user=self.user,
            scenario_keys=("datos_agrupados_y_cards",),
            engine=ScriptedGroupedFactsValidationEngine(),
            run_id="test-run",
        )

        self.assertTrue(report.passed)
        self.assertEqual(report.provider, "openai")
        self.assertEqual(report.usage_summary["event_count"], 2)
        self.assertEqual(report.usage_summary["total_tokens"], 240)
        scenario = report.scenarios[0]
        self.assertEqual(scenario.final_brief["goal"], "muscle_gain")
        self.assertEqual(scenario.turns[0].card_counts["profile"], 1)
        self.assertEqual(scenario.turns[1].card_counts["profile"], 1)
        self.assertTrue(scenario.final_brief["is_ready_for_proposal"])
        self.assertEqual(
            set(scenario.all_tool_names),
            {
                "read_user_profile_context",
                "update_profile_draft",
                "update_proposal_preferences",
                "share_preference_draft_card",
                "share_proposal_preferences_card",
            },
        )
        payload = report.as_dict()
        self.assertTrue(payload["manual_review_required"])
        self.assertFalse(payload["reviewable_proposal_tools_enabled"])

    def test_user_lookup_requires_one_explicit_existing_user(self):
        self.assertEqual(get_validation_user(user_id=self.user.id), self.user)
        self.assertEqual(get_validation_user(email="CM24@EXAMPLE.COM"), self.user)
        with self.assertRaisesMessage(ValueError, "Provide --user-id or --user-email"):
            get_validation_user()

    def test_management_command_requires_explicit_live_confirmation(self):
        with self.assertRaisesMessage(CommandError, "Re-run with --live"):
            call_command(
                "validate_ai_assistant_real_provider",
                user_id=self.user.id,
                stdout=StringIO(),
            )

    def test_management_command_lists_scenarios_without_provider_calls(self):
        output = StringIO()
        call_command(
            "validate_ai_assistant_real_provider",
            list_scenarios=True,
            stdout=output,
        )
        self.assertIn("saludo_y_descubrimiento", output.getvalue())
        self.assertIn("error_de_tool_y_recuperacion", output.getvalue())
    def test_ba06_catalog_contains_targeted_behavioral_scenarios(self):
        catalog = built_in_real_provider_scenarios()
        self.assertIn("tema_externo_breve", catalog)
        self.assertIn("capacidades_en_lenguaje_de_producto", catalog)
        self.assertIn("referencia_ambigua_sin_tools", catalog)
        self.assertIn("ficha_conocida_sin_repreguntas", catalog)
        self.assertEqual(
            catalog["referencia_ambigua_sin_tools"].user_messages,
            ("¿Qué está pasando?",),
        )
        self.assertEqual(catalog["referencia_ambigua_sin_tools"].max_tool_calls, 0)

    def test_profile_scenario_specialization_requires_only_persisted_available_facts(self):
        profile = self.user.profile
        profile.height_cm = 188
        profile.birth_date = None
        profile.sex = ""
        profile.save(update_fields=["height_cm", "birth_date", "sex"])
        record_weight(self.user, weight_kg=85, source="manual")

        scenario = _specialize_scenario_for_user(
            built_in_real_provider_scenarios()["ficha_conocida_sin_repreguntas"],
            user=self.user,
        )

        self.assertEqual(
            scenario.profile_preflight_facts,
            {"weight_kg": 85.0, "height_cm": 188},
        )
        self.assertEqual(
            scenario.profile_preflight_missing_fields,
            ("age_years", "sex"),
        )
        self.assertEqual(scenario.expected_final_brief["weight_kg"], 85.0)
        self.assertEqual(scenario.expected_final_brief["height_cm"], 188)
        self.assertNotIn("age_years", scenario.expected_final_brief)
        self.assertNotIn("sex", scenario.expected_final_brief)
        self.assertIn("weight_kg", scenario.stable_brief_fields)
        self.assertIn("height_cm", scenario.stable_brief_fields)
        self.assertNotIn("age_years", scenario.stable_brief_fields)
        self.assertNotIn("sex", scenario.stable_brief_fields)
        turn = self._profile_validation_turn(
            brief_snapshot={
                "goal": "muscle_gain",
                "requested_entity": "daily_plan",
                "subject_source": "self_profile",
                "weight_kg": 85.0,
                "height_cm": 188,
            }
        )
        self.assertTrue(_expected_brief_check(scenario, (turn,)).passed)

    def test_profile_scenario_specialization_detects_sync_loss_for_complete_ficha(self):
        profile = self.user.profile
        profile.height_cm = 188
        profile.birth_date = date(1988, 1, 17)
        profile.sex = Profile.SEX_MALE
        profile.save(update_fields=["height_cm", "birth_date", "sex"])
        record_weight(self.user, weight_kg=85, source="manual")

        scenario = _specialize_scenario_for_user(
            built_in_real_provider_scenarios()["ficha_conocida_sin_repreguntas"],
            user=self.user,
        )

        self.assertEqual(scenario.profile_preflight_missing_fields, ())
        self.assertEqual(scenario.expected_final_brief["weight_kg"], 85.0)
        self.assertEqual(scenario.expected_final_brief["height_cm"], 188)
        self.assertEqual(
            scenario.expected_final_brief["age_years"],
            calculate_age_years(profile.birth_date),
        )
        self.assertEqual(scenario.expected_final_brief["sex"], Profile.SEX_MALE)
        self.assertTrue(
            {"weight_kg", "height_cm", "age_years", "sex"}.issubset(
                set(scenario.stable_brief_fields)
            )
        )
        turn = self._profile_validation_turn(
            brief_snapshot={
                "goal": "muscle_gain",
                "requested_entity": "daily_plan",
                "subject_source": "self_profile",
                "weight_kg": 85.0,
                "height_cm": 188,
            }
        )
        check = _expected_brief_check(scenario, (turn,))
        self.assertFalse(check.passed)
        self.assertIn("age_years", check.detail)
        self.assertIn("sex", check.detail)

    def _profile_validation_turn(self, *, brief_snapshot):
        return RealProviderValidationTurn(
            index=1,
            turn_id="profile-preflight-1",
            user_message="Usa mi ficha.",
            assistant_message="Revisé los datos disponibles.",
            engine_name="test",
            brief_snapshot=brief_snapshot,
            semantic_intent="capture_nutrition_brief",
            semantic_missing_slots=(),
            tool_results=({"tool_name": "read_user_profile_context", "status": "ok"},),
            card_counts={"profile": 1, "preference": 0, "proposal_preferences": 0},
            card_deltas={"profile": 1, "preference": 0, "proposal_preferences": 0},
            fallback=False,
            fallback_reason="",
            deterministic_runtime_invoked=False,
            provider="openai",
            model="test-real-model",
            usage_observability={"recorded": True},
        )

    def test_known_fact_gate_rejects_same_turn_visible_reask_after_profile_read(self):
        scenario = RealProviderValidationScenario(
            key="pt06-known-profile",
            description="test",
            user_messages=("Usa mi ficha.",),
            fields_not_reasked_after_capture=("weight_kg", "height_cm"),
            visible_reask_markers={
                "weight_kg": ("cuánto pesas",),
                "height_cm": ("cuánto mides",),
            },
        )
        turn = RealProviderValidationTurn(
            index=1,
            turn_id="pt06-known-profile-1",
            user_message="Usa mi ficha.",
            assistant_message="Ya leí tu ficha. ¿Cuánto pesas y cuánto mides?",
            engine_name="test",
            brief_snapshot={"weight_kg": 85.0, "height_cm": 188},
            semantic_intent="capture_nutrition_brief",
            semantic_missing_slots=(),
            tool_results=({"tool_name": "read_user_profile_context", "status": "ok"},),
            card_counts={"profile": 1, "preference": 0, "proposal_preferences": 0},
            card_deltas={"profile": 1, "preference": 0, "proposal_preferences": 0},
            fallback=False,
            fallback_reason="",
            deterministic_runtime_invoked=False,
            provider="openai",
            model="test-real-model",
            usage_observability={"recorded": True},
        )

        check = _known_facts_not_reasked_check(scenario, (turn,))

        self.assertFalse(check.passed)
        self.assertIn("visibly re-asked weight_kg", check.detail)
        self.assertIn("visibly re-asked height_cm", check.detail)

    def test_known_fact_gate_rejects_same_turn_semantic_missing_slot(self):
        scenario = RealProviderValidationScenario(
            key="pt06-known-slot",
            description="test",
            user_messages=("Usa mi ficha.",),
            fields_not_reasked_after_capture=("age_years",),
        )
        turn = RealProviderValidationTurn(
            index=1,
            turn_id="pt06-known-slot-1",
            user_message="Usa mi ficha.",
            assistant_message="Ya tengo tu edad desde la ficha.",
            engine_name="test",
            brief_snapshot={"age_years": 38},
            semantic_intent="capture_nutrition_brief",
            semantic_missing_slots=("age_years",),
            tool_results=({"tool_name": "read_user_profile_context", "status": "ok"},),
            card_counts={"profile": 1, "preference": 0, "proposal_preferences": 0},
            card_deltas={"profile": 1, "preference": 0, "proposal_preferences": 0},
            fallback=False,
            fallback_reason="",
            deterministic_runtime_invoked=False,
            provider="openai",
            model="test-real-model",
            usage_observability={"recorded": True},
        )

        check = _known_facts_not_reasked_check(scenario, (turn,))

        self.assertFalse(check.passed)
        self.assertIn("semantic missing", check.detail)

    def test_behavioral_surface_blocks_unjustified_tools_and_internal_names(self):
        scenario = RealProviderValidationScenario(
            key="ba06-test",
            description="test",
            user_messages=("¿Qué pasó con eso?",),
            max_tool_calls=0,
            forbidden_visible_fragments=("read_proposal",),
        )
        turn = RealProviderValidationTurn(
            index=1,
            turn_id="ba06-test-1",
            user_message="¿Qué pasó con eso?",
            assistant_message="Voy a usar read_proposal.",
            engine_name="test",
            brief_snapshot={},
            semantic_intent="clarify_reference",
            semantic_missing_slots=(),
            tool_results=({"tool_name": "read_proposal", "status": "ok"},),
            card_counts={"profile": 0, "preference": 0, "proposal_preferences": 0},
            card_deltas={"profile": 0, "preference": 0, "proposal_preferences": 0},
            fallback=False,
            fallback_reason="",
            deterministic_runtime_invoked=False,
            provider="openai",
            model="test-real-model",
            usage_observability={"recorded": True},
        )
        check = _behavioral_surface_check(scenario, (turn,))
        self.assertFalse(check.passed)
        self.assertIn("exceeded maximum", check.detail)
        self.assertIn("forbidden visible fragments", check.detail)

    def test_response_repetition_check_rejects_repeated_mechanical_openings(self):
        scenario = RealProviderValidationScenario(
            key="ba06-repeat",
            description="test",
            user_messages=("uno", "dos"),
            max_repeated_opening_count=1,
        )
        base = dict(
            engine_name="test",
            brief_snapshot={},
            semantic_intent="capture_nutrition_brief",
            semantic_missing_slots=(),
            tool_results=(),
            card_counts={"profile": 0, "preference": 0, "proposal_preferences": 0},
            card_deltas={"profile": 0, "preference": 0, "proposal_preferences": 0},
            fallback=False,
            fallback_reason="",
            deterministic_runtime_invoked=False,
            provider="openai",
            model="test-real-model",
            usage_observability={"recorded": True},
        )
        turns = (
            RealProviderValidationTurn(index=1, turn_id="r1", user_message="uno", assistant_message="Perfecto. Quedó registrado.", **base),
            RealProviderValidationTurn(index=2, turn_id="r2", user_message="dos", assistant_message="Perfecto. Sigamos.", **base),
        )
        check = _response_repetition_check(scenario, turns)
        self.assertFalse(check.passed)
        self.assertIn("x2", check.detail)

    def test_structured_provider_contract_reports_parse_and_incomplete_diagnostics(self):
        turn = RealProviderValidationTurn(
            index=1,
            turn_id="cm24-contract-1",
            user_message="Actualiza mi objetivo.",
            assistant_message="{",
            engine_name="test",
            brief_snapshot={},
            semantic_intent="capture_nutrition_brief",
            semantic_missing_slots=(),
            tool_results=(),
            card_counts={"profile": 0, "preference": 0, "proposal_preferences": 0},
            card_deltas={"profile": 0, "preference": 0, "proposal_preferences": 0},
            fallback=False,
            fallback_reason="",
            deterministic_runtime_invoked=False,
            provider="openai",
            model="test-real-model",
            usage_observability={"recorded": True},
            provider_parse_error="invalid_json",
            provider_contract_repair_attempted=True,
            provider_incomplete_reasons=("max_output_tokens",),
            provider_final_incomplete_reason="max_output_tokens",
        )

        check = _structured_provider_contract_check((turn,))

        self.assertFalse(check.passed)
        self.assertIn("parse error", check.detail)
        self.assertIn("max_output_tokens", check.detail)
        self.assertIn("repair retries=1", check.detail)

        recovered = replace(
            turn,
            assistant_message="Respuesta estructurada completa.",
            provider_parse_error="",
            provider_final_incomplete_reason="",
        )
        recovered_check = _structured_provider_contract_check((recovered,))
        self.assertTrue(recovered_check.passed)
        self.assertIn("native function calls=0", recovered_check.detail)
        self.assertIn("repair retries=1", recovered_check.detail)

    def test_structured_provider_contract_accepts_native_function_transport(self):
        turn = RealProviderValidationTurn(
            index=1,
            turn_id="cm24-native-1",
            user_message="Actualiza mi objetivo.",
            assistant_message="Perfecto, dejé el objetivo registrado.",
            engine_name="test",
            brief_snapshot={"goal": "fat_loss"},
            semantic_intent="capture_nutrition_brief",
            semantic_missing_slots=(),
            tool_results=({"tool_name": "update_proposal_preferences", "status": "ok"},),
            card_counts={"profile": 0, "preference": 0, "proposal_preferences": 0},
            card_deltas={"profile": 0, "preference": 0, "proposal_preferences": 0},
            fallback=False,
            fallback_reason="",
            deterministic_runtime_invoked=False,
            provider="openai",
            model="test-real-model",
            usage_observability={"recorded": True},
            provider_native_tool_transport=True,
            provider_native_tool_calls=1,
        )

        check = _structured_provider_contract_check((turn,))

        self.assertTrue(check.passed)
        self.assertIn("native function calls=1", check.detail)

    def test_tool_result_grounding_rejects_false_unavailable_claim(self):
        turn = RealProviderValidationTurn(
            index=1,
            turn_id="cm24-test-1",
            user_message="Usa read_proposal.",
            assistant_message="No tengo ejecución de herramientas disponible.",
            engine_name="test",
            brief_snapshot={},
            semantic_intent="read_context",
            semantic_missing_slots=(),
            tool_results=({"tool_name": "read_proposal", "status": "error"},),
            card_counts={"profile": 0, "preference": 0, "proposal_preferences": 0},
            card_deltas={"profile": 0, "preference": 0, "proposal_preferences": 0},
            fallback=False,
            fallback_reason="",
            deterministic_runtime_invoked=False,
            provider="openai",
            model="test-real-model",
            usage_observability={"recorded": True},
        )

        check = _tool_result_grounding_check((turn,))

        self.assertFalse(check.passed)
        self.assertIn("contradicted executed tool result", check.detail)

    def test_provider_followup_health_is_release_blocking_and_names_error(self):
        turn = RealProviderValidationTurn(
            index=1,
            turn_id="pt-followup-1",
            user_message="Déjalo en cuatro comidas.",
            assistant_message="La dirección de la propuesta quedó actualizada.",
            engine_name="test",
            brief_snapshot={"meals_per_day": 4},
            semantic_intent="capture_nutrition_brief",
            semantic_missing_slots=(),
            tool_results=({"tool_name": "update_proposal_preferences", "status": "ok"},),
            card_counts={"profile": 0, "preference": 0, "proposal_preferences": 0},
            card_deltas={"profile": 0, "preference": 0, "proposal_preferences": 0},
            fallback=False,
            fallback_reason="",
            deterministic_runtime_invoked=False,
            provider="openai",
            model="test-real-model",
            usage_observability={"recorded": True},
            tool_followup_local_ack=True,
            tool_followup_local_ack_policy="state_ack_only.v2",
            provider_tool_followup_failed=True,
            provider_tool_followup_error_status=400,
            provider_tool_followup_error_type="invalid_request_error",
            provider_tool_followup_error_code="tool_output_missing",
            provider_tool_followup_error_message=(
                "No tool output found for function call call_abc123."
            ),
            provider_tool_followup_error_param="input",
            provider_tool_followup_error_request_id="req_123",
        )

        check = _provider_followup_health_check((turn,))

        self.assertFalse(check.passed)
        self.assertIn("status=400", check.detail)
        self.assertIn("tool_output_missing", check.detail)
        self.assertIn("req_123", check.detail)
        self.assertIn("No tool output found", check.detail)

        healthy = replace(
            turn,
            assistant_message="Listo, quedó en cuatro comidas.",
            tool_followup_local_ack=False,
            provider_tool_followup_failed=False,
            provider_tool_followup_error_status=None,
            provider_tool_followup_error_type="",
            provider_tool_followup_error_code="",
            provider_tool_followup_error_message="",
            provider_tool_followup_error_param="",
            provider_tool_followup_error_request_id="",
        )
        healthy_check = _provider_followup_health_check((healthy,))
        self.assertTrue(healthy_check.passed)

    def test_provider_followup_health_rejects_local_ack_text_on_healthy_tool_turn(self):
        turn = RealProviderValidationTurn(
            index=1,
            turn_id="pt05-healthy-local-copy",
            user_message="Déjalo en cuatro comidas.",
            assistant_message="La dirección de la propuesta quedó actualizada.",
            engine_name="test",
            brief_snapshot={"meals_per_day": 4},
            semantic_intent="capture_nutrition_brief",
            semantic_missing_slots=(),
            tool_results=({"tool_name": "update_proposal_preferences", "status": "ok"},),
            card_counts={"profile": 0, "preference": 0, "proposal_preferences": 0},
            card_deltas={"profile": 0, "preference": 0, "proposal_preferences": 0},
            fallback=False,
            fallback_reason="",
            deterministic_runtime_invoked=False,
            provider="openai",
            model="test-real-model",
            usage_observability={"recorded": True, "status": "completed"},
            tool_followup_local_ack=False,
            provider_tool_followup_failed=False,
        )

        check = _provider_followup_health_check((turn,))

        self.assertFalse(check.passed)
        self.assertIn("healthy tool turn reproduced local acknowledgement", check.detail)

    def test_post_tool_fallback_pacing_rejects_backend_selected_next_question(self):
        turn = RealProviderValidationTurn(
            index=1,
            turn_id="cm24-local-ack-1",
            user_message="Déjalo en 3 comidas y avancemos.",
            assistant_message=(
                "Perfecto, dejé registrado comidas: 3 al día. "
                "Para seguir, cuéntame si quieres usar tu ficha personal."
            ),
            engine_name="test",
            brief_snapshot={"meals_per_day": 3},
            semantic_intent="capture_nutrition_brief",
            semantic_missing_slots=(),
            tool_results=({"tool_name": "update_proposal_preferences", "status": "ok"},),
            card_counts={"profile": 0, "preference": 0, "proposal_preferences": 0},
            card_deltas={"profile": 0, "preference": 0, "proposal_preferences": 0},
            fallback=False,
            fallback_reason="",
            deterministic_runtime_invoked=False,
            provider="openai",
            model="test-real-model",
            usage_observability={"recorded": True},
            tool_followup_local_ack=True,
            tool_followup_local_ack_policy="state_ack_only.v2",
            provider_tool_followup_failed=True,
        )

        check = _post_tool_fallback_pacing_check((turn,))

        self.assertFalse(check.passed)
        self.assertIn("selected a follow-up question", check.detail)

        corrected = replace(
            turn,
            assistant_message=(
                "Perfecto. La propuesta queda como un programa semanal para bajar grasa, "
                "con 3 comidas al día."
            ),
        )
        corrected_check = _post_tool_fallback_pacing_check((corrected,))
        self.assertTrue(corrected_check.passed)
        self.assertIn("remained state-only", corrected_check.detail)

