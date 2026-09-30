"""Verify persisted program contents, not merely tool invocation."""

from notas.application.dto.program_proposal import parse_program_payload
from notas.application.queries.proposal_simulation_queries import simulate_proposal_payload
from notas.domain.models import NutritionProposal

PROGRAM_SCENARIOS = ("programa_completo_1_semana", "programa_completo_8_semanas", "programa_culinario_progresivo_8_semanas")


def build_program_scenarios(scenario_type):
    scenarios = {key: scenario_type(
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
    key = PROGRAM_SCENARIOS[2]
    scenarios[key] = scenario_type(
        key=key, description="Culinary 56-day program: progressive energy, PPK interval, strict fat cap and produce diversity.",
        user_messages=("Crea una propuesta revisable de programa culinario de 8 semanas, cuatro comidas diarias. "
            "Peso medido 85 kg. Usa explícitamente peso proyectado lineal desde 85 hasta 80 kg como referencia de proteína, "
            "no como medición ni garantía. Calorías diarias objetivo por semana: 2500, 2385.71, 2271.43, 2157.14, 2042.86, "
            "1928.57, 1814.29, 1700. Acepto tolerancia de calorías del 3%. Cada día proteína entre 2 y 2.2 g/kg "
            "y grasa nunca superior al 25% de las calorías reales. Mínimos diarios: 200 g de fruta y 250 g de verduras; "
            "por semana al menos tres frutas y tres verduras distintas. Máximo tres repeticiones de una familia de comidas "
            "por horario y semana. Usa program_specification versión 1 y energía manual; no apliques ni calendarices.",),
        expected_final_brief={"requested_entity": "program", "duration_weeks": 8, "meals_per_day": 4},
        required_tool_names=("update_proposal_preferences", "create_nutrition_engine_dailyplan_proposal_from_drafts"),
        max_tool_calls=10, capability_ids=("PG-08", "DP-13"), fixture_requirements=("culinary_library",),
        mutation_policy="proposal_only", ground_truth={"duration_weeks": 8}, expected_outcome="nutrition_proposal",
        default_enabled=False, manual_review_prompts=(
            "¿Son deseables las preparaciones y razonables las porciones? No puntuar únicamente los macros.",
            "¿Distingue variantes cercanas de familias diferentes y comunica que falta revisión humana de las candidatas?",))
    return scenarios


def program_proposal_check(scenario, *, user, previous_ids):
    if scenario.key not in PROGRAM_SCENARIOS:
        return None
    proposals = list(NutritionProposal.objects.filter(created_by=user).exclude(pk__in=previous_ids))
    if len(proposals) != 1:
        return False, f"Expected one program proposal; observed {len(proposals)}."
    proposal = proposals[0]
    if proposal.status != NutritionProposal.STATUS_PENDING_REVIEW or proposal.applied_at:
        return False, "Program must remain pending review and unapplied."
    if scenario.key == PROGRAM_SCENARIOS[2]:
        return _culinary_proposal_check(user, proposal)
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


def _culinary_proposal_check(user, proposal):
    from notas.application.ai_intake.culinary_program import revalidate_culinary_proposal

    try:
        spec = proposal.targets["program_specification"]
        expected = {"duration_weeks": 8, "meals_per_day": 4, "weight_basis": "projected", "measured_weight_kg": 85,
                    "protein_min_ppk": 2, "protein_max_ppk": 2.2, "fat_max_percent": 25,
                    "calorie_tolerance_percent": 3, "fruit_min_g": 200, "vegetable_min_g": 250,
                    "weekly_fruit_species": 3, "weekly_vegetable_species": 3, "max_family_per_week_per_slot": 3}
        if any(spec.get(key) != value for key, value in expected.items()):
            return False, "Captured program requirements differ from the explicit request."
        for index, week in enumerate(spec["weeks"]):
            if abs(week["kcal"] - (2500 - 800 * index / 7)) > .02 or abs(week["projected_weight_kg"] - (85 - 5 * index / 7)) > .011:
                return False, "Weekly energy or projected weight trajectory differs."
        validation = revalidate_culinary_proposal(user=user, proposal=proposal)
        return validation["valid"], "Independent validation of all 56 days, culinary bounds and weekly diversity. Human review still required."
    except (ValueError, KeyError) as exc:
        return False, str(exc)
