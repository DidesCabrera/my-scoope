from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any

from nutrition_solver.application.contracts import OptimizationStatus
from nutrition_solver.application.optimizer_v2 import (
    OptimizationBackend,
    OptimizationPlanResultV2,
    solve_optimization_problem,
)
from nutrition_solver.application.problem_v2 import MealSlotProblem, NutrientRange, OptimizationProblemV2
from nutrition_solver.application.quality import assess_optimization_quality
from nutrition_solver.application.shadow import compare_solver_backends
from nutrition_solver.domain.meal_grammar import archetypes_for_meal_kind

from notas.application.dto.proposal_payloads import (
    CREATE_DAILYPLAN_INTENT,
    ProposedDailyPlanDTO,
    ProposedDailyPlanMealDTO,
    ProposedDailyPlanPayloadDTO,
    ProposedFoodItemDTO,
    ProposedMealDTO,
)
from notas.application.nutrition_engine.meal_templates import build_dailyplan_meal_templates
from notas.application.queries.solver_food_candidates import (
    build_solver_food_profile,
    get_solver_food_candidate_queryset,
)


@dataclass(frozen=True)
class DailyPlanOptimizerV2Outcome:
    payload: dict
    solver_summary: dict


class DailyPlanOptimizerV2Error(ValueError):
    pass


def build_dailyplan_optimization_problem(
    *,
    user,
    target_plan,
    meals_per_day: int,
    excluded_terms: tuple[str, ...] | list[str] = (),
    preferred_terms: tuple[str, ...] | list[str] = (),
    time_limit_ms: int = 1500,
) -> OptimizationProblemV2:
    rows = tuple(get_solver_food_candidate_queryset(user)[:250])
    normalized_exclusions = tuple(_normalize_text(term) for term in excluded_terms if term)
    normalized_preferences = tuple(_normalize_text(term) for term in preferred_terms if term)
    usable_rows = tuple(
        row for row in rows if not _matches_any(_normalize_text(row.name), normalized_exclusions)
    )
    profiles = tuple(build_solver_food_profile(row, required=False) for row in usable_rows)
    if not profiles:
        raise DailyPlanOptimizerV2Error("dailyplan_optimizer_v2_requires_solver_enabled_foods")

    templates = build_dailyplan_meal_templates(meals_per_day)
    slots = []
    for template in templates:
        archetypes = archetypes_for_meal_kind(template.kind)
        if not archetypes:
            raise DailyPlanOptimizerV2Error(f"dailyplan_optimizer_v2_missing_archetype:{template.kind}")
        slots.append(
            MealSlotProblem(
                slot_id=f"meal_{template.index}",
                meal_kind=template.kind,
                nutrient_ranges=_meal_ranges(target_plan, template.kcal_allocation),
                allowed_archetypes=archetypes,
            )
        )

    preferred_food_ids = tuple(
        row.id
        for row in usable_rows
        if _matches_any(_normalize_text(row.name), normalized_preferences)
    )
    return OptimizationProblemV2(
        food_profiles=profiles,
        meal_slots=tuple(slots),
        daily_nutrient_ranges=_daily_ranges(target_plan),
        preferences={"preferred_food_ids": preferred_food_ids},
        time_limit_ms=time_limit_ms,
    )


def run_dailyplan_optimizer_v2(
    *,
    user,
    target_plan,
    meals_per_day: int,
    plan_name: str,
    excluded_terms: tuple[str, ...] | list[str] = (),
    preferred_terms: tuple[str, ...] | list[str] = (),
    backend: OptimizationBackend | str = OptimizationBackend.CP_SAT_V1,
    shadow_enabled: bool = False,
    shadow_backend: OptimizationBackend | str = OptimizationBackend.CP_SAT_V1,
    time_limit_ms: int = 1500,
) -> DailyPlanOptimizerV2Outcome:
    problem = build_dailyplan_optimization_problem(
        user=user,
        target_plan=target_plan,
        meals_per_day=meals_per_day,
        excluded_terms=excluded_terms,
        preferred_terms=preferred_terms,
        time_limit_ms=time_limit_ms,
    )
    selected_backend = OptimizationBackend(backend)
    result = solve_optimization_problem(problem, backend=selected_backend)
    if result.status == OptimizationStatus.IMPOSSIBLE:
        raise DailyPlanOptimizerV2Error(
            f"dailyplan_optimizer_v2_impossible:{result.diagnostics.get('reason', 'unknown')}"
        )

    quality = assess_optimization_quality(problem, result)
    summary: dict[str, Any] = {
        "contract_version": "nutrition_solver_optimization.v2",
        "active_backend": selected_backend.value,
        "active_result": result.as_dict(),
        "quality": quality.as_dict(),
        "shadow_enabled": bool(shadow_enabled),
    }
    if shadow_enabled:
        comparison = compare_solver_backends(
            problem,
            active_backend=selected_backend,
            shadow_backend=shadow_backend,
        )
        summary["shadow_comparison"] = comparison.as_dict()
        summary["telemetry"] = comparison.as_telemetry()

    return DailyPlanOptimizerV2Outcome(
        payload=_build_payload(
            result=result,
            meals_per_day=meals_per_day,
            plan_name=plan_name,
        ),
        solver_summary=summary,
    )


def build_shadow_summary_for_legacy_generator(
    *,
    user,
    target_plan,
    meals_per_day: int,
    excluded_terms: tuple[str, ...] | list[str] = (),
    preferred_terms: tuple[str, ...] | list[str] = (),
    shadow_backend: OptimizationBackend | str = OptimizationBackend.CP_SAT_V1,
    time_limit_ms: int = 1500,
) -> dict:
    try:
        problem = build_dailyplan_optimization_problem(
            user=user,
            target_plan=target_plan,
            meals_per_day=meals_per_day,
            excluded_terms=excluded_terms,
            preferred_terms=preferred_terms,
            time_limit_ms=time_limit_ms,
        )
    except DailyPlanOptimizerV2Error as exc:
        return {
            "contract_version": "nutrition_solver_optimization.v2",
            "active_backend": "legacy_generator_v6",
            "shadow_enabled": True,
            "shadow_status": "unavailable",
            "reason": str(exc),
        }
    shadow_result = solve_optimization_problem(problem, backend=shadow_backend)
    return {
        "contract_version": "nutrition_solver_optimization.v2",
        "active_backend": "legacy_generator_v6",
        "shadow_enabled": True,
        "shadow_backend": OptimizationBackend(shadow_backend).value,
        "shadow_result": shadow_result.as_dict(),
        "shadow_quality": assess_optimization_quality(problem, shadow_result).as_dict(),
        "visible_payload_source": "legacy_generator_v6",
    }


def _build_payload(
    *,
    result: OptimizationPlanResultV2,
    meals_per_day: int,
    plan_name: str,
) -> dict:
    templates = build_dailyplan_meal_templates(meals_per_day)
    template_by_slot = {f"meal_{template.index}": template for template in templates}
    meals = []
    for meal in result.meals:
        template = template_by_slot[meal.slot_id]
        meals.append(
            ProposedDailyPlanMealDTO(
                hour=template.hour,
                note=(
                    f"{template.label} optimizado con {result.backend.value}; "
                    "revisar composición y porciones antes de aplicar."
                ),
                meal=ProposedMealDTO(
                    name=f"{template.label} NSO {template.index + 1}",
                    foods=[
                        ProposedFoodItemDTO(food_id=portion.food_id, quantity=portion.quantity_g)
                        for portion in meal.portions
                    ],
                ),
            )
        )
    return ProposedDailyPlanPayloadDTO(
        intent=CREATE_DAILYPLAN_INTENT,
        dailyplan=ProposedDailyPlanDTO(name=plan_name, meals=meals),
    ).as_dict()


def _meal_ranges(target_plan, allocation: float) -> tuple[NutrientRange, ...]:
    return tuple(
        NutrientRange(metric, target * allocation, target * allocation * minimum, target * allocation * maximum, weight)
        for metric, target, minimum, maximum, weight in (
            ("kcal", float(target_plan.total_kcal), 0.72, 1.28, 3),
            ("protein", float(target_plan.protein), 0.55, 1.45, 3),
            ("carbs", float(target_plan.carbs), 0.50, 1.50, 1.5),
            ("fat", float(target_plan.fat), 0.45, 1.55, 1.5),
        )
    )


def _daily_ranges(target_plan) -> tuple[NutrientRange, ...]:
    return tuple(
        NutrientRange(metric, target, target * minimum, target * maximum, weight)
        for metric, target, minimum, maximum, weight in (
            ("kcal", float(target_plan.total_kcal), 0.88, 1.12, 4),
            ("protein", float(target_plan.protein), 0.82, 1.18, 4),
            ("carbs", float(target_plan.carbs), 0.78, 1.22, 2),
            ("fat", float(target_plan.fat), 0.75, 1.25, 2),
        )
    )


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    return " ".join("".join(char for char in normalized if not unicodedata.combining(char)).split())


def _matches_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(term and term in value for term in terms)
