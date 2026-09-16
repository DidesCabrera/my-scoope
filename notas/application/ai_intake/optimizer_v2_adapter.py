from __future__ import annotations

import unicodedata
from dataclasses import dataclass, replace
from typing import Any

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
from nutrition_solver.application.contracts import OptimizationStatus, SolverConstraint
from nutrition_solver.application.optimizer_v2 import (
    OptimizationBackend,
    OptimizationPlanResultV2,
    solve_optimization_alternatives,
    solve_optimization_problem,
)
from nutrition_solver.application.problem_v2 import MealSlotProblem, NutrientRange, OptimizationProblemV2
from nutrition_solver.application.quality import assess_optimization_quality
from nutrition_solver.application.shadow import compare_solver_backends
from nutrition_solver.domain.capabilities import SolverFeatureKey
from nutrition_solver.domain.meal_grammar import archetypes_for_meal_kind


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
    dietary_pattern: str | None = None,
    allergies_or_intolerances: tuple[str, ...] | list[str] = (),
    cooking_time_preference: str | None = None,
    budget_preference: str | None = None,
    simplicity_preference: str | None = None,
    variety_preference: str | None = None,
    time_limit_ms: int = 1500,
) -> OptimizationProblemV2:
    rows = tuple(get_solver_food_candidate_queryset(user)[:250])
    normalized_exclusions = tuple(_normalize_text(term) for term in excluded_terms if term)
    normalized_preferences = tuple(_normalize_text(term) for term in preferred_terms if term)
    usable_rows = tuple(
        row for row in rows if not _matches_any(_normalize_text(row.name), normalized_exclusions)
    )
    profiles = tuple(build_solver_food_profile(row, required=False) for row in usable_rows)
    profiles = _filter_profiles_by_typed_safety_constraints(
        profiles,
        dietary_pattern=dietary_pattern,
        allergies_or_intolerances=allergies_or_intolerances,
    )
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
    constraints = []
    normalized_variety = _normalize_text(variety_preference or "")
    if normalized_variety in {"high", "alta", "alto"}:
        constraints.append(
            SolverConstraint(
                "max_food_repetitions",
                "hard",
                {"count": max(1, (meals_per_day + 1) // 2)},
                "Preferencia explícita por alta variedad.",
            )
        )
    return OptimizationProblemV2(
        food_profiles=profiles,
        meal_slots=tuple(slots),
        daily_nutrient_ranges=_daily_ranges(target_plan),
        constraints=tuple(constraints),
        preferences={
            "preferred_food_ids": preferred_food_ids,
            "cooking_time_preference": _normalize_text(cooking_time_preference or ""),
            "budget_preference": _normalize_text(budget_preference or ""),
            "simplicity_preference": _normalize_text(simplicity_preference or ""),
            "variety_preference": normalized_variety,
        },
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
    dietary_pattern: str | None = None,
    allergies_or_intolerances: tuple[str, ...] | list[str] = (),
    cooking_time_preference: str | None = None,
    budget_preference: str | None = None,
    simplicity_preference: str | None = None,
    variety_preference: str | None = None,
    alternative_count: int = 3,
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
        dietary_pattern=dietary_pattern,
        allergies_or_intolerances=allergies_or_intolerances,
        cooking_time_preference=cooking_time_preference,
        budget_preference=budget_preference,
        simplicity_preference=simplicity_preference,
        variety_preference=variety_preference,
        time_limit_ms=time_limit_ms,
    )
    selected_backend = OptimizationBackend(backend)
    portfolio = solve_optimization_alternatives(
        problem,
        count=alternative_count,
        backend=selected_backend,
    )
    if not portfolio.alternatives:
        raise DailyPlanOptimizerV2Error(
            "dailyplan_optimizer_v2_impossible:no_feasible_alternative"
        )
    ranked = []
    for raw_result in portfolio.alternatives:
        if raw_result.status == OptimizationStatus.IMPOSSIBLE:
            continue
        quality = assess_optimization_quality(problem, raw_result)
        result = _result_with_product_quality_status(raw_result, quality)
        ranked.append((result, quality))
    ranked.sort(
        key=lambda item: (
            -item[1].nutritional_score,
            -item[1].functional_score,
            item[0].objective_value,
        )
    )
    if not ranked:
        raise DailyPlanOptimizerV2Error("dailyplan_optimizer_v2_impossible:no_acceptable_alternative")
    result, quality = ranked[0]
    alternatives = [
        {
            "alternative_id": f"alternative_{index}",
            "label": f"Alternativa {index}",
            "rank": index,
            "payload": _build_payload(
                result=candidate,
                meals_per_day=meals_per_day,
                plan_name=plan_name,
            ),
            "result": candidate.as_dict(),
            "quality": candidate_quality.as_dict(),
        }
        for index, (candidate, candidate_quality) in enumerate(ranked, start=1)
    ]
    summary: dict[str, Any] = {
        "contract_version": "nutrition_solver_optimization.v2",
        "active_backend": selected_backend.value,
        "active_result": result.as_dict(),
        "quality": quality.as_dict(),
        "quality_status": result.status.value,
        "requested_alternative_count": max(1, min(int(alternative_count), 10)),
        "alternative_count": len(alternatives),
        "selected_alternative_id": "alternative_1",
        "alternatives": alternatives,
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


def _filter_profiles_by_typed_safety_constraints(
    profiles,
    *,
    dietary_pattern: str | None,
    allergies_or_intolerances: tuple[str, ...] | list[str],
):
    pattern = _normalize_text(dietary_pattern or "")
    allergies = _expanded_allergen_terms(allergies_or_intolerances)
    accepted_dietary_tags = {
        "vegan": {"vegan", "vegano", "vegana"},
        "vegano": {"vegan", "vegano", "vegana"},
        "vegetarian": {"vegan", "vegano", "vegana", "vegetarian", "vegetariano", "vegetariana"},
        "vegetariano": {"vegan", "vegano", "vegana", "vegetarian", "vegetariano", "vegetariana"},
        "pescatarian": {
            "vegan", "vegano", "vegana", "vegetarian", "vegetariano", "vegetariana",
            "pescatarian", "pescetariano", "pescetariana",
        },
    }.get(pattern)

    compatible = []
    for profile in profiles:
        dietary_tags = _profile_feature_strings(profile, SolverFeatureKey.DIETARY_TAGS)
        allergens = _profile_feature_strings(profile, SolverFeatureKey.ALLERGENS)
        if accepted_dietary_tags is not None and not dietary_tags.intersection(accepted_dietary_tags):
            continue
        if allergies and (not allergens or allergens.intersection(allergies)):
            continue
        compatible.append(profile)
    return tuple(compatible)


def _profile_feature_strings(profile, key: SolverFeatureKey) -> set[str]:
    feature = profile.feature(key)
    if feature is None or not feature.available:
        return set()
    values = feature.value if isinstance(feature.value, (tuple, list, set)) else (feature.value,)
    return {_normalize_text(value) for value in values if value}


def _expanded_allergen_terms(values: tuple[str, ...] | list[str]) -> set[str]:
    groups = (
        {"milk", "dairy", "lactose", "leche", "lactosa", "lacteos", "lacteos"},
        {"gluten", "wheat", "trigo", "cebada", "barley", "rye", "centeno"},
        {"nuts", "tree nuts", "peanut", "peanuts", "frutos secos", "mani", "maní"},
        {"shellfish", "crustaceans", "mariscos", "crustaceos", "crustáceos"},
        {"soy", "soya", "soja"},
        {"egg", "eggs", "huevo", "huevos"},
        {"fish", "pescado"},
        {"sesame", "sesamo", "sésamo"},
    )
    declared = {_normalize_text(value) for value in values if value}
    expanded = set(declared)
    for group in groups:
        normalized_group = {_normalize_text(value) for value in group}
        if declared.intersection(normalized_group):
            expanded.update(normalized_group)
    return expanded


def _result_with_product_quality_status(result, quality):
    if not quality.hard_constraints_satisfied:
        status = OptimizationStatus.IMPOSSIBLE
    elif quality.nutritional_score >= 92 and quality.functional_score >= 90:
        status = OptimizationStatus.OPTIMAL
    elif quality.nutritional_score >= 80 and quality.functional_score >= 80:
        status = OptimizationStatus.ACCEPTABLE
    else:
        status = OptimizationStatus.PARTIAL
    return replace(
        result,
        status=status,
        diagnostics={
            **dict(result.diagnostics),
            "mathematical_solver_status": result.diagnostics.get("solver_status"),
            "product_quality_status": status.value,
        },
    )
