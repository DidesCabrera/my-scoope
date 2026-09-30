"""Shared culinary validation for generation, revision and approval, without chat state."""

from notas.application.culinary_library import load_culinary_candidates
from notas.application.dto.program_proposal import parse_program_payload
from notas.application.nutrition_engine.meal_templates import build_dailyplan_meal_templates
from nutrition_solver.application.culinary_planner import validate_culinary_program
from nutrition_solver.application.program_specification import parse_program_specification


def program_slots(spec):
    return [{"kind": item.kind, "hour": item.hour, "allocation": item.kcal_allocation}
            for item in build_dailyplan_meal_templates(spec.meals_per_day)]


def revalidate_culinary_proposal(*, user, proposal):
    """Validate the actual payload against current food data and approved requirements."""
    from copy import deepcopy
    from types import SimpleNamespace

    spec = parse_program_specification(proposal.targets["program_specification"])
    raw = proposal.current_snapshot.get("nutrition_brief") or {}
    brief = SimpleNamespace(excluded_foods=raw.get("excluded_foods", []),
                            allergies_or_intolerances=raw.get("allergies_or_intolerances", []),
                            dietary_pattern=raw.get("dietary_pattern"))
    catalog = proposal.current_snapshot.get("culinary_catalog", [])
    candidates, rejected = load_culinary_candidates(user=user, brief=brief, variant_ids=[c["variant_id"] for c in catalog])
    if rejected or len(candidates) != len(catalog):
        raise ValueError("culinary_catalog_changed_since_review")
    weeks = deepcopy(proposal.current_snapshot.get("culinary_weeks", []))
    parsed = parse_program_payload(proposal.proposed_payload)
    if parsed.duration_weeks != spec.duration_weeks:
        raise ValueError("program_spec_duration_conflict")
    for day in parsed.days:
        rows = sorted((row for row in weeks[day.week_number - 1] if row["day"] == day.day_number), key=lambda row: row["slot"])
        if len(rows) != len(day.dailyplan.meals):
            raise ValueError("culinary_proposal_composition_changed")
        for row, meal in zip(rows, day.dailyplan.meals):
            row["foods"] = [food.as_dict() for food in meal.meal.foods]
            if row["preparation"] != meal.note or row["name"] != meal.meal.name:
                raise ValueError("culinary_proposal_preparation_changed")
    result = validate_culinary_program(spec, weeks, program_slots(spec), candidates)
    if not result["valid"]:
        raise ValueError("culinary_program_requirements_failed:" + ",".join(result["errors"]))
    return result
