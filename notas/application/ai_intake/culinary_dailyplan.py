"""Adapt validated culinary variants into reviewable DailyPlan payloads."""

from __future__ import annotations

from dataclasses import dataclass

from notas.application.culinary_library import load_culinary_candidates
from notas.application.dto.proposal_payloads import (
    CREATE_DAILYPLAN_INTENT,
    ProposedDailyPlanDTO,
    ProposedDailyPlanMealDTO,
    ProposedDailyPlanPayloadDTO,
    ProposedFoodItemDTO,
    ProposedMealDTO,
)
from notas.application.nutrition_engine.meal_templates import build_dailyplan_meal_templates
from nutrition_solver.application.culinary_day_planner import solve_culinary_day_alternatives
from nutrition_solver.application.culinary_planner import CulinaryPlanningError

CULINARY_DAILYPLAN_VERSION = "culinary_variants_dailyplan_v1"


@dataclass(frozen=True)
class CulinaryDailyPlanOutcome:
    payload: dict
    solver_summary: dict


def try_build_culinary_dailyplan(
    *,
    user,
    brief,
    target_plan,
    meals_per_day: int,
    plan_name: str,
    alternative_count: int,
    time_limit_ms: int,
) -> tuple[CulinaryDailyPlanOutcome | None, dict]:
    candidates, rejected = load_culinary_candidates(user=user, brief=brief)
    templates = build_dailyplan_meal_templates(meals_per_day)
    required_kinds = {template.kind for template in templates}
    available_kinds = {kind for candidate in candidates for kind in candidate.meal_kinds}
    readiness = {
        "candidate_count": len(candidates),
        "rejected_count": len(rejected),
        "required_meal_kinds": sorted(required_kinds),
        "available_meal_kinds": sorted(available_kinds),
        "missing_meal_kinds": sorted(required_kinds - available_kinds),
    }
    if not candidates or required_kinds - available_kinds:
        readiness["status"] = "insufficient"
        readiness["fallback_reason"] = "culinary_catalog_incomplete"
        return None, readiness

    slots = tuple(
        {
            "kind": template.kind,
            "allocation": template.kcal_allocation,
            "label": template.label,
            "hour": template.hour,
        }
        for template in templates
    )
    targets = {
        "kcal": float(target_plan.total_kcal),
        "protein": float(target_plan.protein),
        "carbs": float(target_plan.carbs),
        "fat": float(target_plan.fat),
    }
    try:
        solutions = solve_culinary_day_alternatives(
            targets=targets,
            slots=slots,
            candidates=candidates,
            count=alternative_count,
            time_limit_seconds=max(float(time_limit_ms) / 1000, 0.1),
        )
    except CulinaryPlanningError as exc:
        readiness["status"] = "infeasible"
        readiness["fallback_reason"] = exc.code
        readiness["details"] = exc.details
        return None, readiness

    alternatives = []
    for index, solution in enumerate(solutions, start=1):
        payload = _payload_from_solution(plan_name=plan_name, templates=templates, solution=solution)
        alternatives.append({
            "alternative_id": f"culinary_{index}",
            "label": f"Alternativa culinaria {index}",
            "rank": index,
            "payload": payload,
            "result": solution.as_dict(),
            "quality": _quality(targets=targets, actual=solution.totals),
        })
    readiness["status"] = "ready"
    summary = {
        "contract_version": "nutrition_solver_optimization.v2",
        "planner_version": CULINARY_DAILYPLAN_VERSION,
        "active_backend": "culinary_variants_cp_sat_v1",
        "configured_backend": "culinary_primary",
        "candidate_source": "validated_culinary_variants",
        "raw_food_fallback_used": False,
        "catalog_readiness": readiness,
        "requested_alternative_count": max(1, min(int(alternative_count), 10)),
        "alternative_count": len(alternatives),
        "selected_alternative_id": "culinary_1",
        "alternatives": alternatives,
        "culinary_selections": _selection_evidence(solutions[0]),
    }
    return CulinaryDailyPlanOutcome(payload=alternatives[0]["payload"], solver_summary=summary), readiness


def _payload_from_solution(*, plan_name, templates, solution):
    meals = []
    for row in solution.meals:
        template = templates[row["slot"]]
        meals.append(ProposedDailyPlanMealDTO(
            hour=template.hour,
            note=f"{row['preparation']} · Variante culinaria validada; porciones ajustadas al objetivo.",
            meal=ProposedMealDTO(
                name=row["name"],
                foods=[
                    ProposedFoodItemDTO(
                        food_id=food["food_id"],
                        quantity=food["quantity"],
                        unit=food["unit"],
                    )
                    for food in row["foods"]
                ],
            ),
        ))
    return ProposedDailyPlanPayloadDTO(
        intent=CREATE_DAILYPLAN_INTENT,
        dailyplan=ProposedDailyPlanDTO(name=plan_name, meals=meals),
    ).as_dict()


def _quality(*, targets, actual):
    deviations = [abs(float(actual[key]) - float(targets[key])) / float(targets[key]) for key in targets]
    score = max(0.0, 100.0 * (1.0 - sum(deviations) / len(deviations)))
    return {
        "nutritional_score": round(score, 2),
        "functional_score": 100.0,
        "hard_constraints_satisfied": True,
        "warnings": [],
    }


def _selection_evidence(solution):
    return [
        {
            "slot": row["slot"],
            "variant_id": row["variant_id"],
            "family": row["family"],
            "evidence_digest": row["evidence_digest"],
            "validation_level": row["validation_level"],
            "components": row["components"],
            "foods": row["foods"],
        }
        for row in solution.meals
    ]
