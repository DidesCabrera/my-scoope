from django.test import TestCase

from ai_assistant.application.tools import TOOL_CREATE_VALIDATED_MEAL_PROPOSAL
from notas.application.ai_intake.conversation_replay import (
    ConversationReplayScenario,
    assistant_envelope,
    ensure_replay_user,
    get_replay_scenario,
    run_replay_scenario,
    tool_request,
)
from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    NutritionConversationMessage,
    NutritionConversationState,
    build_intake_result_from_brief,
)
from notas.domain.models import DailyPlan, Food, Meal, NutritionProposal


class AiAssistantConversationReplayTests(TestCase):
    def assert_replay_invariants(self, result):
        outcomes = result.invariant_outcomes()
        failures = [outcome for outcome in outcomes if not outcome.passed]
        self.assertEqual(
            failures,
            [],
            msg="; ".join(f"{failure.key}: {failure.detail}" for failure in failures),
        )

    def test_json_visible_boundary_scenario_prevents_raw_structured_envelope(self):
        result = run_replay_scenario(get_replay_scenario("json_visible_boundary"))

        self.assert_replay_invariants(result)
        self.assertEqual(result.final_brief.requested_entity, "daily_plan")
        self.assertIn("objetivo", result.visible_messages[-1].lower())

    def test_dieta_con_ficha_tool_led_scenario_satisfies_state_card_and_persistence_invariants(self):
        result = run_replay_scenario(get_replay_scenario("dieta_con_ficha_tool_led"))
        brief = result.final_brief

        self.assert_replay_invariants(result)
        self.assertEqual(brief.goal, "muscle_gain")
        self.assertEqual(brief.subject_source, "self_profile")
        self.assertEqual(result.final_card_counts["profile"], 2)
        self.assertEqual(result.final_card_counts["preference"], 1)
        self.assertEqual(result.final_card_counts["proposal_preferences"], 1)

        latest_profile_card = [
            message.profile_draft_card
            for message in result.final_state.messages
            if message.profile_draft_card
        ][-1]
        profile_items = {item["key"]: item for item in latest_profile_card["items"]}
        self.assertEqual(profile_items["weight_kg"]["value"], "84 kg")
        self.assertEqual(profile_items["height_cm"]["value"], "188 cm")
        self.assertEqual(profile_items["age_years"]["value"], "38 años")
        self.assertEqual(profile_items["sex"]["value"], "Hombre")
        self.assertEqual(profile_items["activity_level"]["value"], "Alta")
        self.assertEqual(profile_items["weight_kg"]["source"], "profile")
        self.assertEqual(profile_items["age_years"]["source"], "chat_draft")

    def test_grouped_facts_can_arrive_in_one_turn_without_automatic_cards(self):
        result = run_replay_scenario(get_replay_scenario("datos_agrupados_orden_libre"))

        self.assert_replay_invariants(result)
        self.assertEqual(result.turns[0].profile_card_delta, 0)
        self.assertEqual(result.turns[0].preference_card_delta, 0)
        self.assertEqual(result.turns[0].proposal_preferences_card_delta, 0)
        self.assertEqual(result.turns[1].profile_card_delta, 1)
        self.assertEqual(result.turns[1].preference_card_delta, 1)
        self.assertEqual(result.turns[1].proposal_preferences_card_delta, 1)
        self.assertEqual(result.final_brief.age_years, 38)
        self.assertEqual(result.final_brief.meals_per_day, 4)
        self.assertIn("simple", result.final_brief.style_preferences)

    def test_change_direction_is_an_expected_transition_not_a_replay_failure(self):
        result = run_replay_scenario(get_replay_scenario("cambio_direccion"))

        self.assert_replay_invariants(result)
        self.assertEqual(result.final_brief.requested_entity, "program")
        self.assertEqual(result.final_brief.goal, "fat_loss")
        self.assertEqual(result.final_brief.meals_per_day, 3)
        self.assertEqual(result.final_card_counts["proposal_preferences"], 0)

    def test_ba06_off_domain_capability_and_ambiguity_replays_stay_tool_free(self):
        for scenario_key in (
            "tema_externo_breve",
            "capacidades_sin_internals",
            "referencia_ambigua_sin_tools",
        ):
            with self.subTest(scenario=scenario_key):
                result = run_replay_scenario(get_replay_scenario(scenario_key))
                self.assert_replay_invariants(result)
                self.assertEqual(result.all_tool_names, ())
                self.assertEqual(result.final_card_counts, {
                    "profile": 0,
                    "preference": 0,
                    "proposal_preferences": 0,
                })

    def test_replay_reports_invalid_provider_intent_as_contract_failure(self):
        scenario = ConversationReplayScenario(
            key="provider_contract_failure",
            description="Malformed fake-provider semantics fail through the provider contract invariant.",
            user_messages=("¿Qué puedes hacer?",),
            provider_responses=(
                assistant_envelope(
                    "Puedo ayudarte dentro de My Scoope.",
                    intent="unsupported_replay_intent",
                ),
            ),
            max_tool_calls=0,
        )

        result = run_replay_scenario(scenario, assert_clean=False)
        outcomes = {outcome.key: outcome for outcome in result.invariant_outcomes()}

        self.assertFalse(outcomes["provider_contract"].passed)
        self.assertIn("Invalid name", outcomes["provider_contract"].detail)
        self.assertEqual(result.all_tool_names, ())

    def test_reviewable_proposal_replay_uses_real_tool_without_applying_final_objects(self):
        user = ensure_replay_user("ai_replay_proposal_user")
        dailyplan = DailyPlan.objects.create(name="Día base replay", created_by=user)
        food = Food.objects.create(
            name="Pechuga replay",
            protein=31,
            carbs=0,
            fat=3.6,
            created_by=user,
        )
        scenario = ConversationReplayScenario(
            key="propuesta_revisable_real",
            description="Create a real pending-review proposal through a typed product tool.",
            user_messages=("Crea una propuesta revisable de almuerzo con pollo.",),
            provider_responses=(
                assistant_envelope(
                    "Crearé una propuesta revisable, sin aplicarla automáticamente.",
                    intent="create_meal_proposal",
                    tool_requests=(
                        tool_request(
                            TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
                            {
                                "dailyplan_id": dailyplan.id,
                                "title": "Almuerzo replay",
                                "summary": "Propuesta creada por el harness CM22.",
                                "targets": {"protein": 60},
                                "proposed_payload": {
                                    "intent": "create_meal",
                                    "meal": {
                                        "name": "Almuerzo replay",
                                        "foods": [
                                            {"food_id": food.id, "quantity": 200},
                                        ],
                                    },
                                },
                            },
                            reason="Crear una propuesta real pendiente de revisión.",
                        ),
                    ),
                    requires_human_review=True,
                ),
                assistant_envelope(
                    "Listo. La propuesta quedó pendiente de revisión y no se aplicó al plan.",
                    intent="create_meal_proposal",
                    requires_human_review=True,
                ),
            ),
            required_tool_names=(TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,),
            expected_reviewable_proposal_delta=1,
            required_visible_fragments=("pendiente de revisión",),
            expected_final_card_counts={
                "profile": 0,
                "preference": 0,
                "proposal_preferences": 0,
            },
        )

        meal_count_before = Meal.objects.filter(created_by=user).count()
        result = run_replay_scenario(scenario, user=user)

        self.assert_replay_invariants(result)
        self.assertEqual(Meal.objects.filter(created_by=user).count(), meal_count_before)
        proposal = NutritionProposal.objects.get(created_by=user, title="Almuerzo replay")
        self.assertEqual(proposal.status, NutritionProposal.STATUS_PENDING_REVIEW)
        self.assertEqual(proposal.source, NutritionProposal.SOURCE_AI)
        self.assertIsNone(proposal.applied_at)

    def test_last_assistant_message_ignores_empty_card_messages(self):
        state = NutritionConversationState(
            messages=[
                NutritionConversationMessage(role="assistant", text="Texto visible."),
                NutritionConversationMessage(role="assistant", text="", profile_draft_card={"title": "Ficha"}),
            ],
            result=build_intake_result_from_brief(NutritionBrief(raw_prompt="test")),
        )

        self.assertEqual(state.last_assistant_message, "Texto visible.")
