"""Build a reviewable program from persisted culinary variants, never raw food bags."""

import logging
from dataclasses import asdict
from time import monotonic

from django.db import transaction

from notas.application.culinary_library import load_culinary_candidates
from notas.application.dto.program_proposal import parse_program_payload
from notas.application.queries.proposal_simulation_queries import simulate_proposal_payload
from notas.application.services.nutrition.culinary_validation import program_slots, revalidate_culinary_proposal
from notas.domain.models import NutritionProposal, NutritionProposalAuditEvent
from nutrition_solver.application.culinary_planner import (
    CulinaryPlanningError,
    solve_culinary_week,
    validate_culinary_program,
)
from nutrition_solver.application.program_specification import parse_program_specification


def build_culinary_program(*, user, brief):
    logger = logging.getLogger("myscoope.assistant.runtime")
    spec = parse_program_specification(brief.program_specification)
    if brief.duration_weeks not in (None, spec.duration_weeks) or brief.meals_per_day not in (None, spec.meals_per_day):
        raise ValueError("program_spec_brief_conflict")
    if any((brief.macro_distribution, brief.protein_target, brief.carb_target, brief.fat_target, brief.protein_per_kg_target)):
        raise ValueError("program_spec_conflicting_scalar_targets_clear_or_reconcile")
    if brief.calorie_target is not None and any(abs(week.kcal - brief.calorie_target) > .01 for week in spec.weeks):
        raise ValueError("program_spec_conflicting_scalar_calories")
    candidates, rejected = load_culinary_candidates(user=user, brief=brief)
    if not candidates:
        raise CulinaryPlanningError("culinary_catalog_requires_validated_meals", rejected=rejected)
    slots, weeks = program_slots(spec), []
    for week in spec.weeks:
        started = monotonic()
        logger.info("culinary_week_start week=%s candidates=%s", week.week, len(candidates))
        try:
            rows = solve_culinary_week(spec, week, slots, candidates, previous=weeks[-1] if weeks else ())
        except CulinaryPlanningError as exc:
            if exc.code != "culinary_candidate_pool_infeasible":
                raise
            # Widen only the search portfolio, never relax the user's constraints.
            rows = solve_culinary_week(spec, week, slots, candidates, previous=weeks[-1] if weeks else (), candidate_width=6)
        weeks.append(rows)
        logger.info("culinary_week_done week=%s seconds=%.3f", week.week, monotonic() - started)
    logger.info("culinary_validation_start days=%s", 7 * spec.duration_weeks)
    return persist_culinary_program(user=user, brief=brief, spec=spec, slots=slots, candidates=candidates, weeks=weeks)


def persist_culinary_program(*, user, brief, spec, slots, candidates, weeks, revision=None):
    validation = validate_culinary_program(spec, weeks, slots, candidates)
    if not validation["valid"]:
        raise CulinaryPlanningError("culinary_independent_validation_failed", errors=validation["errors"])
    logger = logging.getLogger("myscoope.assistant.runtime")
    logger.info("culinary_validation_done days=%s", len(validation["days"]))
    days = []
    for target, rows in zip(spec.weeks, weeks):
        for day in range(1, 8):
            meals = [{"hour": slots[row["slot"]]["hour"], "note": row["preparation"],
                      "meal": {"name": row["name"], "foods": row["foods"]}}
                     for row in rows if row["day"] == day]
            days.append({"week_number": target.week, "day_number": day,
                         "dailyplan": {"name": f"Semana {target.week} · Día {day}", "meals": meals}})
    payload = parse_program_payload({"intent": "create_program", "program": {
        "name": "Programa alimentario personalizado", "duration_weeks": spec.duration_weeks, "days": days}}).as_dict()
    logger.info("culinary_simulation_start")
    simulation = simulate_proposal_payload(user, payload).as_dict()
    logger.info("culinary_simulation_done")
    selected = {row["variant_id"] for week in weeks for row in week}
    catalog_evidence = [candidate.as_dict() for candidate in candidates if candidate.variant_id in selected]
    warnings = []
    if any(candidate["validation_level"] != "human_validated" for candidate in catalog_evidence):
        warnings.append("Incluye variantes validadas por reglas, aún pendientes de revisión culinaria humana.")
    summary = {"payload_validation": {"is_valid": True, "intent": "create_program"}, "simulation": simulation,
               "requirements": validation, "days": validation["days"], "warnings": warnings,
               "variety": {"families": len({row["family"] for week in weeks for row in week}),
                           "variants": len(selected), "max_family_per_week_per_slot": spec.max_family_per_week_per_slot},
               "requires_human_review": True}
    with transaction.atomic():
        proposal = NutritionProposal.objects.create(
            created_by=user, status=NutritionProposal.STATUS_PENDING_REVIEW, source=NutritionProposal.SOURCE_AI,
            title="Programa culinario personalizado", summary=f"{spec.duration_weeks} semanas con objetivos propios; límites verificados en cada día. Pendiente de aprobación.",
            targets={"program_specification": spec.as_dict()}, proposed_payload=payload,
            current_snapshot={"source": "culinary_program.v1", "nutrition_brief": asdict(brief),
                              "culinary_weeks": weeks, "culinary_catalog": catalog_evidence,
                              "revision": revision or {}}, validation_summary=summary)
        NutritionProposalAuditEvent.objects.create(proposal=proposal, actor=user,
            action=NutritionProposalAuditEvent.ACTION_CREATED, status_before="", status_after=proposal.status,
            message="Programa culinario calculado y validado; pendiente de aprobación.",
            metadata={"intent": "create_program", "day_count": 7 * spec.duration_weeks})
    logger.info("culinary_proposal_saved proposal_id=%s status=%s", proposal.pk, proposal.status)
    return proposal


def revise_culinary_program(*, user, proposal_id, week_numbers, meal_numbers, avoid_food_ids=()):
    from copy import deepcopy

    from notas.application.ai_intake.nutrition_brief import deserialize_brief

    source = NutritionProposal.objects.filter(pk=proposal_id, created_by=user).first()
    if source is None or source.status in {NutritionProposal.STATUS_REJECTED, NutritionProposal.STATUS_CANCELLED}:
        raise ValueError("proposal_not_allowed")
    if source.current_snapshot.get("source") != "culinary_program.v1":
        raise ValueError("culinary_program_revision_requires_culinary_source")
    revalidate_culinary_proposal(user=user, proposal=source)
    spec = parse_program_specification(source.targets["program_specification"])
    for values, maximum in ((week_numbers, spec.duration_weeks), (meal_numbers, spec.meals_per_day)):
        if not isinstance(values, list) or not values or len(values) != len(set(values)) or any(type(v) is not int or not 1 <= v <= maximum for v in values):
            raise ValueError("culinary_revision_scope_invalid")
    if not isinstance(avoid_food_ids, (list, tuple)) or any(type(v) is not int or v < 1 for v in avoid_food_ids):
        raise ValueError("culinary_revision_food_ids_invalid")
    brief = deserialize_brief(source.current_snapshot["nutrition_brief"])
    candidates, _ = load_culinary_candidates(user=user, brief=brief)
    slots, weeks = program_slots(spec), deepcopy(source.current_snapshot["culinary_weeks"])
    for number in sorted(week_numbers):
        rows = weeks[number - 1]
        pinned = {(row["day"], row["slot"]): row for row in rows if row["slot"] + 1 not in meal_numbers}
        changed = {(row["day"], row["slot"]): row["variant_id"] for row in rows if row["slot"] + 1 in meal_numbers}
        weeks[number - 1] = solve_culinary_week(spec, spec.weeks[number - 1], slots, candidates,
            previous=weeks[number - 2] if number > 1 else (), pinned=pinned, changed_from=changed,
            avoid_food_ids=avoid_food_ids, candidate_width=6)
    return persist_culinary_program(user=user, brief=brief, spec=spec, slots=slots, candidates=candidates, weeks=weeks,
        revision={"source_proposal_id": source.pk, "week_numbers": week_numbers, "meal_numbers": meal_numbers,
                  "avoid_food_ids": list(avoid_food_ids), "unselected_meals_preserved": True})
