"""Verify persisted program contents, not merely tool invocation."""

from notas.application.dto.program_proposal import parse_program_payload
from notas.application.queries.proposal_simulation_queries import simulate_proposal_payload
from notas.domain.models import NutritionProposal

PROGRAM_SCENARIOS = ("programa_completo_1_semana", "programa_completo_8_semanas")


def build_program_scenarios(scenario_type):
    return {key: scenario_type(
        key=key, description=f"Complete reviewable {weeks}-week nutrition program.",
        user_messages=(f"Crea ahora una propuesta revisable de programa alimentario completo de {weeks} semanas, "
            "con siete días por semana y cuatro comidas diarias. Cada día debe aportar 2400 kcal, "
            "30% proteína, 50% carbohidratos y 20% grasas. Usa hombre de 38 años, 80 kg, 180 cm y "
            "actividad alta. Puedes rotar menús, pero indica cuántos son distintos. No lo apliques ni lo calendarices.",),
        expected_final_brief={"requested_entity": "program", "duration_weeks": weeks, "meals_per_day": 4},
        required_tool_names=("update_proposal_preferences", "create_nutrition_engine_dailyplan_proposal_from_drafts"),
        max_tool_calls=10, capability_ids=("PG-08", "DP-13"),
        fixture_requirements=("solver_candidates",), mutation_policy="proposal_only",
        ground_truth={"duration_weeks": weeks, "meals_per_day": 4, "calorie_target": 2400},
        expected_outcome="nutrition_proposal", default_enabled=False,
        manual_review_prompts=("¿Respeta la duración y comunica la repetición real, los avisos y la aprobación pendiente?",),
    ) for key, weeks in zip(PROGRAM_SCENARIOS, (1, 8))}


def program_proposal_check(scenario, *, user, previous_ids):
    if scenario.key not in PROGRAM_SCENARIOS:
        return None
    proposals = list(NutritionProposal.objects.filter(created_by=user).exclude(pk__in=previous_ids))
    if len(proposals) != 1:
        return False, f"Expected one program proposal; observed {len(proposals)}."
    proposal = proposals[0]
    if proposal.status != NutritionProposal.STATUS_PENDING_REVIEW or proposal.applied_at:
        return False, "Program must remain pending review and unapplied."
    try:
        parsed = parse_program_payload(proposal.proposed_payload)
        current = simulate_proposal_payload(user, proposal.proposed_payload).as_dict()
    except ValueError as exc:
        return False, str(exc)
    if parsed.duration_weeks != scenario.ground_truth["duration_weeks"]:
        return False, "Program duration differs from the user's request."
    if proposal.targets.get("total_kcal") != 2400:
        return False, "Stored energy target differs from 2400 kcal."
    for day in current["program"]["days"]:
        daily = day["dailyplan"]
        if len(daily["meals"]) != 4:
            return False, "A day lacks the four requested meals."
        for metric, target, tolerance in (("total_kcal", 2400, .12), ("protein", 180, .20), ("carbs", 300, .25), ("fat", 53.3333, .25)):
            if abs(daily["kpis"][metric] - target) > target * tolerance:
                return False, f"Week {day['week_number']} day {day['day_number']} exceeds {metric} tolerance."
    return True, f"Verified {parsed.duration_weeks * 7} complete days, four meals each, targets and review boundary."
