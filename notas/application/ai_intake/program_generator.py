"""Generate complete nutrition programs for human review."""

from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json

from django.db import transaction

from notas.application.ai_intake.dailyplan_generator import (
    _build_dailyplan_payload_with_solver_summary, _build_validation_summary,
    _build_subject_context_snapshot, build_dailyplan_target_plan,
)
from notas.application.ai_intake.nutrition_brief import apply_subject_context
from notas.application.dto.program_proposal import parse_program_payload
from notas.application.queries.proposal_simulation_queries import simulate_proposal_payload
from notas.domain.models import NutritionProposal, NutritionProposalAuditEvent


def create_weekly_program_proposal(*, user, brief):
    duration = brief.duration_weeks
    if type(duration) is not int or not 1 <= duration <= 8:
        raise ValueError("program_proposal_duration_must_be_1_to_8")
    daily_brief = apply_subject_context(replace(brief, requested_entity="daily_plan"), user=user)
    target = build_dailyplan_target_plan(user=user, brief=daily_brief)
    payload, solver = _build_dailyplan_payload_with_solver_summary(user=user, brief=daily_brief, target_plan=target, alternative_count=7)
    alternatives = [item["payload"] for item in solver.get("alternatives", [])
                    if item.get("payload") and item.get("quality", {}).get("hard_constraints_satisfied") is True]
    if solver.get("alternatives") and not alternatives:
        raise ValueError("program_proposal_no_safe_daily_menus")
    candidates = alternatives or [payload]
    # Recalculate every candidate independently; do not inherit the best candidate's grade.
    checked = []
    for candidate in candidates:
        simulation = simulate_proposal_payload(user, candidate).as_dict()
        validation = _build_validation_summary(brief=daily_brief, target_plan=target, simulation=simulation, solver_summary=solver)
        if validation["engine_validation"]["is_valid"] and not validation["engine_validation"]["has_errors"]:
            checked.append((candidate, validation))
    if not checked:
        raise ValueError("program_proposal_no_valid_daily_menus")
    days, validations, fingerprints = [], [], set()
    for index in range(7 * duration):
        candidate, validation = deepcopy(checked[index % len(checked)])
        week, day = index // 7 + 1, index % 7 + 1
        candidate["dailyplan"]["name"] = f"Semana {week} · Día {day}"
        days.append({"week_number": week, "day_number": day, "dailyplan": candidate["dailyplan"]})
        validations.append({"week_number": week, "day_number": day, "target_comparison": validation["target_comparison"], "engine_validation": validation["engine_validation"]})
        composition = [[food["food_id"] for food in item["meal"]["foods"]] for item in candidate["dailyplan"]["meals"]]
        fingerprints.add(hashlib.sha256(json.dumps(composition, sort_keys=True).encode()).hexdigest())
    program_payload = parse_program_payload({"intent": "create_program", "program": {
        "name": "Programa alimentario personalizado", "duration_weeks": duration, "days": days,
    }}).as_dict()
    simulation = simulate_proposal_payload(user, program_payload).as_dict()
    with transaction.atomic():
        proposal = NutritionProposal.objects.create(
            created_by=user, status=NutritionProposal.STATUS_PENDING_REVIEW, source=NutritionProposal.SOURCE_AI,
            title="Programa alimentario personalizado", summary=f"{duration} semanas completas ({7 * duration} días), {brief.meals_per_day or 4} comidas por día; rotación de {len(fingerprints)} menús distintos. Los objetivos diarios se mantienen durante el programa. Revisa las repeticiones antes de aprobar.",
            targets=target.as_targets_dict(), proposed_payload=program_payload,
            current_snapshot={"source": "weekly_program.v1", "subject_context": _build_subject_context_snapshot(brief=daily_brief, target_plan=target),
                              "nutrition_brief": asdict(brief)},
            validation_summary={"payload_validation": {"is_valid": True, "intent": "create_program"},
                "simulation": simulation, "days": validations,
                "variety": {"unique_daily_menus": len(fingerprints), "days": 7 * duration,
                            "repeated_menus": len(fingerprints) < 7 * duration},
                "requires_human_review": True},
        )
        NutritionProposalAuditEvent.objects.create(proposal=proposal, actor=user,
            action=NutritionProposalAuditEvent.ACTION_CREATED, status_before="", status_after=proposal.status,
            message="Programa calculado, pendiente de aprobación.", metadata={"intent": "create_program", "day_count": 7 * duration})
    return proposal


def program_proposal_tool_summary(proposal):
    """Keep 56-day evidence in storage; send the model a bounded, truthful summary."""
    program = proposal.proposed_payload["program"]
    validation = proposal.validation_summary
    warnings = list(dict.fromkeys(str(issue["message"]) for day in validation["days"]
        for issue in day["engine_validation"].get("issues", []) if issue.get("message")))
    totals = [day["dailyplan"]["kpis"] for day in validation["simulation"]["program"]["days"]]
    return {"id": proposal.pk, "title": proposal.title, "summary": proposal.summary,
        "status": proposal.status, "status_label": proposal.get_status_display(), "source": proposal.source,
        "proposal_type": "program", "targets": proposal.targets,
        "proposed_payload": {"intent": "create_program", "program": {
            "name": program["name"], "duration_weeks": program["duration_weeks"], "day_count": len(program["days"])}},
        "validation_summary": {"payload_validation": validation["payload_validation"],
            "variety": validation["variety"], "warnings": warnings[:12], "warning_count": len(warnings),
            "daily_ranges": {metric: {"minimum": min(day[metric] for day in totals), "maximum": max(day[metric] for day in totals)}
                for metric in ("total_kcal", "protein", "carbs", "fat")},
            "all_days_validated": len(validation["days"]) == len(program["days"]),
            "full_content_available_in_proposal_review": True, "applied": False}}
