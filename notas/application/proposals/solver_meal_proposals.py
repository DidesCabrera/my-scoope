from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from django.conf import settings
from django.db import transaction

from notas.application.culinary_library import load_culinary_candidates, normalized
from notas.application.dto.proposal_payloads import CREATE_MEAL_INTENT
from notas.application.queries.solver_food_candidates import (
    DEFAULT_SOLVER_FOOD_CANDIDATE_LIMIT,
    list_solver_food_candidates,
)
from notas.application.services.commands.proposal_commands import (
    NutritionProposalCreateResult,
    create_validated_meal_proposal,
)
from notas.domain.models import Food, NutritionProposal
from nutrition_solver.application.contracts import (
    OptimizationInput,
    OptimizationStatus,
    SolverConstraint,
    optimize_meal_portions,
)
from nutrition_solver.application.culinary_day_planner import solve_culinary_meal
from nutrition_solver.application.culinary_planner import CulinaryPlanningError
from nutrition_solver.domain.models import MacroTarget

SOLVER_MEAL_PROPOSAL_VERSION = "nutrition_solver_meal_proposal_v1"
DEFAULT_SOLVER_MEAL_CANDIDATE_LIMIT = 40
DEFAULT_ENERGY_ONLY_MACRO_DISTRIBUTION = {
    "protein": 30.0,
    "carbs": 50.0,
    "fat": 20.0,
}


@dataclass(frozen=True)
class SolverMealProposalResult:
    proposal: NutritionProposal
    optimization_result: Any
    candidate_count: int

    def as_dict(self) -> dict:
        return {
            "proposal_id": self.proposal.id,
            "optimization_result": self.optimization_result.as_dict(),
            "candidate_count": self.candidate_count,
        }


@dataclass(frozen=True)
class CulinaryMealOptimizationResult:
    status: OptimizationStatus
    meal: dict
    totals: dict
    solver_status: str

    def as_dict(self) -> dict:
        return {
            "status": self.status.value,
            "strategy": "validated_culinary_variant_then_portions",
            "meal": dict(self.meal),
            "totals": dict(self.totals),
            "solver_status": self.solver_status,
        }


@transaction.atomic
def create_solver_generated_meal_proposal(
    *,
    user,
    dailyplan_id: int,
    title: str,
    target: Mapping[str, Any],
    search: str | None = None,
    limit: int = DEFAULT_SOLVER_MEAL_CANDIDATE_LIMIT,
    include_extended: bool = True,
    meal_slot: str = "Solver meal",
    summary: str = "",
    source: str = NutritionProposal.SOURCE_AI,
    constraints: tuple[SolverConstraint, ...] = (),
) -> SolverMealProposalResult:
    """Create a reviewable Meal proposal from the deterministic solver.

    This command is a notas-side orchestration boundary:
    - it reads operational candidates through the S8 adapter;
    - it sends pure candidates to ``nutrition_solver``;
    - it persists only a reviewable ``NutritionProposal``;
    - it never creates or applies final Meal/MealFood/DailyPlan rows.
    """

    clean_title = _normalize_title(title)
    macro_target = _parse_macro_target(target)
    culinary_result, culinary_readiness = _try_culinary_meal(
        user=user,
        target=macro_target,
        meal_slot=meal_slot,
        search=search,
        limit=limit,
    )
    if culinary_result is not None:
        proposed_payload = _build_culinary_create_meal_payload(
            meal_name=culinary_result.meal["name"],
            meal=culinary_result.meal,
        )
        proposal_result = create_validated_meal_proposal(
            user=user,
            dailyplan_id=dailyplan_id,
            title=clean_title,
            summary=_build_culinary_summary(summary=summary, result=culinary_result),
            source=source,
            targets=macro_target.as_dict(),
            proposed_payload=proposed_payload,
        )
        _attach_culinary_validation_summary(
            proposal_result=proposal_result,
            result=culinary_result,
            readiness=culinary_readiness,
            target=macro_target,
        )
        return SolverMealProposalResult(
            proposal=proposal_result.proposal,
            optimization_result=culinary_result,
            candidate_count=culinary_readiness["candidate_count"],
        )
    if not bool(getattr(settings, "NUTRITION_CULINARY_RAW_FALLBACK_ENABLED", True)):
        raise ValueError(culinary_readiness["fallback_reason"])

    candidates_result = list_solver_food_candidates(
        user,
        search=search,
        limit=_normalize_limit(limit),
        include_extended=include_extended,
    )
    if candidates_result.total_eligible_count == 0:
        raise ValueError("nutrition_solver_no_eligible_candidates")
    optimization_result = optimize_meal_portions(
        OptimizationInput(
            target=macro_target,
            candidate_foods=candidates_result.candidates,
            meal_slots=(meal_slot or clean_title,),
            constraints=constraints,
            context={
                "source": "notas.application.proposals.solver_meal_proposals",
                "dailyplan_id": int(dailyplan_id),
                "search": candidates_result.search,
                "include_extended": bool(include_extended),
            },
        )
    )

    if optimization_result.status == OptimizationStatus.IMPOSSIBLE:
        raise ValueError("nutrition_solver_meal_proposal_impossible")

    proposed_payload = _build_create_meal_payload(
        meal_name=clean_title,
        optimization_result=optimization_result,
        portion_units=dict(
            Food.objects.filter(
                pk__in=[portion.food_id for portion in optimization_result.portions]
            ).values_list("id", "portion_unit")
        ),
    )

    if not proposed_payload["meal"]["foods"]:
        raise ValueError("nutrition_solver_meal_proposal_requires_positive_portions")

    proposal_result = create_validated_meal_proposal(
        user=user,
        dailyplan_id=dailyplan_id,
        title=clean_title,
        summary=_build_summary(summary=summary, optimization_result=optimization_result),
        source=source,
        targets=macro_target.as_dict(),
        proposed_payload=proposed_payload,
    )
    _attach_solver_validation_summary(
        proposal_result=proposal_result,
        optimization_result=optimization_result,
        candidates_result=candidates_result,
        target=macro_target,
        culinary_readiness=culinary_readiness,
    )

    return SolverMealProposalResult(
        proposal=proposal_result.proposal,
        optimization_result=optimization_result,
        candidate_count=candidates_result.count,
    )


def _try_culinary_meal(*, user, target, meal_slot, search, limit):
    if not bool(getattr(settings, "NUTRITION_CULINARY_PRIMARY_ENABLED", True)):
        return None, {"status": "disabled", "fallback_reason": "culinary_primary_disabled", "candidate_count": 0}
    candidates, rejected = load_culinary_candidates(user=user)
    meal_kind = _meal_kind_from_slot(meal_slot)
    if search:
        term = normalized(search)
        candidates = tuple(
            candidate for candidate in candidates
            if term in normalized(" ".join([
                candidate.name,
                candidate.family,
                *(ingredient.name for ingredient in candidate.ingredients),
            ]))
        )
    compatible = tuple(candidate for candidate in candidates if meal_kind in candidate.meal_kinds)[: _normalize_limit(limit)]
    readiness = {
        "status": "ready" if compatible else "insufficient",
        "candidate_count": len(compatible),
        "rejected_count": len(rejected),
        "meal_kind": meal_kind,
    }
    if not compatible:
        readiness["fallback_reason"] = "culinary_catalog_slot_unavailable"
        return None, readiness
    try:
        solution = solve_culinary_meal(
            target=target.as_dict(),
            meal_kind=meal_kind,
            candidates=compatible,
            time_limit_seconds=max(float(getattr(settings, "NUTRITION_SOLVER_TIME_LIMIT_MS", 1500)) / 1000, 0.1),
        )
    except CulinaryPlanningError as exc:
        readiness.update({"status": "infeasible", "fallback_reason": exc.code, "details": exc.details})
        return None, readiness
    meal = solution.meals[0]
    return CulinaryMealOptimizationResult(
        status=OptimizationStatus.OPTIMAL if solution.solver_status == "OPTIMAL" else OptimizationStatus.ACCEPTABLE,
        meal=meal,
        totals=solution.totals,
        solver_status=solution.solver_status,
    ), readiness


def _meal_kind_from_slot(value):
    text = normalized(value or "")
    if any(term in text for term in ("desayuno", "breakfast")):
        return "breakfast"
    if any(term in text for term in ("cena", "dinner")):
        return "dinner"
    if any(term in text for term in ("snack", "colacion", "media manana", "merienda")):
        return "snack"
    return "main"


def _build_culinary_create_meal_payload(*, meal_name, meal):
    return {
        "intent": CREATE_MEAL_INTENT,
        "meal": {
            "name": meal_name,
            "foods": [
                {
                    "food_id": int(food["food_id"]),
                    "quantity": round(float(food["quantity"]), 2),
                    "unit": food["unit"],
                }
                for food in meal["foods"]
            ],
        },
    }


def _build_culinary_summary(*, summary, result):
    base = (summary or "").strip()
    generated = f"Comida seleccionada desde una variante culinaria validada y ajustada por porciones. Estado: {result.status.value}."
    return f"{base} · {generated}" if base else generated


def _attach_culinary_validation_summary(*, proposal_result, result, readiness, target):
    proposal = proposal_result.proposal
    validation_summary = dict(proposal.validation_summary or {})
    validation_summary["nutrition_solver"] = {
        "version": "nutrition_solver_meal_proposal_v2_culinary",
        "status": result.status.value,
        "target": target.as_dict(),
        "result": result.as_dict(),
        "culinary_primary": readiness,
        "raw_food_fallback_used": False,
        "source_boundary": {
            "candidate_source": "notas.CulinaryVariant",
            "applies_changes": False,
            "requires_human_review": True,
        },
    }
    current_snapshot = dict(proposal.current_snapshot or {})
    current_snapshot["culinary_selection"] = [{
        "slot": 0,
        "variant_id": result.meal["variant_id"],
        "family": result.meal["family"],
        "evidence_digest": result.meal["evidence_digest"],
        "validation_level": result.meal["validation_level"],
        "components": result.meal["components"],
        "foods": result.meal["foods"],
    }]
    proposal.validation_summary = validation_summary
    proposal.current_snapshot = current_snapshot
    proposal.save(update_fields=["validation_summary", "current_snapshot"])


def _parse_macro_target(target: Mapping[str, Any]) -> MacroTarget:
    if not isinstance(target, Mapping):
        raise ValueError("nutrition_solver_target_must_be_object")

    kcal = _required_positive_float(target, "kcal", aliases=("total_kcal", "calories"))
    macro_aliases = {
        "protein": ("protein_g",),
        "carbs": ("carbs_g", "carbohydrates"),
        "fat": ("fat_g",),
    }
    supplied_macros = {
        key: _first_present_value(target, key, aliases=aliases)
        for key, aliases in macro_aliases.items()
    }
    distribution = _normalize_meal_macro_distribution(target.get("macro_distribution"))
    if distribution and any(value is not None for value in supplied_macros.values()):
        raise ValueError("nutrition_solver_target_macro_modes_conflict")
    if distribution:
        protein = kcal * distribution["protein"] / 100 / 4
        carbs = kcal * distribution["carbs"] / 100 / 4
        fat = kcal * distribution["fat"] / 100 / 9
    elif all(value is None for value in supplied_macros.values()):
        protein = kcal * DEFAULT_ENERGY_ONLY_MACRO_DISTRIBUTION["protein"] / 100 / 4
        carbs = kcal * DEFAULT_ENERGY_ONLY_MACRO_DISTRIBUTION["carbs"] / 100 / 4
        fat = kcal * DEFAULT_ENERGY_ONLY_MACRO_DISTRIBUTION["fat"] / 100 / 9
    elif any(value is None for value in supplied_macros.values()):
        raise ValueError("nutrition_solver_target_macros_must_be_complete")
    else:
        protein = _required_positive_float(target, "protein", aliases=("protein_g",))
        carbs = _required_positive_float(target, "carbs", aliases=("carbs_g", "carbohydrates"))
        fat = _required_positive_float(target, "fat", aliases=("fat_g",))

    return MacroTarget(
        kcal=kcal,
        protein=protein,
        carbs=carbs,
        fat=fat,
    )


def _normalize_meal_macro_distribution(value: object) -> dict[str, float] | None:
    if value in (None, {}):
        return None
    if not isinstance(value, Mapping):
        raise ValueError("nutrition_target_distribution_must_be_complete")
    try:
        distribution = {
            key: float(value[key])
            for key in ("protein", "carbs", "fat")
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("nutrition_target_distribution_must_be_complete") from exc
    if min(distribution.values()) <= 0:
        raise ValueError("nutrition_target_distribution_must_be_positive")
    if abs(sum(distribution.values()) - 100.0) > 0.01:
        raise ValueError("nutrition_target_distribution_must_sum_100")
    if not 15 <= distribution["fat"] <= 35:
        raise ValueError("nutrition_target_distribution_fat_out_of_supported_range")
    return distribution


def _first_present_value(
    target: Mapping[str, Any],
    key: str,
    *,
    aliases: tuple[str, ...] = (),
):
    for candidate_key in (key, *aliases):
        if candidate_key in target:
            return target.get(candidate_key)
    return None


def _required_positive_float(
    target: Mapping[str, Any],
    key: str,
    *,
    aliases: tuple[str, ...] = (),
) -> float:
    raw_value = None
    for candidate_key in (key, *aliases):
        if candidate_key in target:
            raw_value = target.get(candidate_key)
            break

    if isinstance(raw_value, bool):
        raise ValueError(f"nutrition_solver_target_{key}_must_be_positive_number")

    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"nutrition_solver_target_{key}_must_be_positive_number") from exc

    if value <= 0:
        raise ValueError(f"nutrition_solver_target_{key}_must_be_positive_number")

    return value


def _build_create_meal_payload(*, meal_name: str, optimization_result, portion_units: Mapping[int, str]) -> dict:
    return {
        "intent": CREATE_MEAL_INTENT,
        "meal": {
            "name": meal_name,
            "foods": [
                {
                    "food_id": int(portion.food_id),
                    "quantity": round(float(portion.quantity_g), 2),
                    "unit": portion_units.get(int(portion.food_id), "g"),
                }
                for portion in optimization_result.portions
                if float(portion.quantity_g) > 0
            ],
        },
    }


def _attach_solver_validation_summary(
    *,
    proposal_result: NutritionProposalCreateResult,
    optimization_result,
    candidates_result,
    target: MacroTarget,
    culinary_readiness: Mapping[str, Any] | None = None,
) -> None:
    proposal = proposal_result.proposal
    validation_summary = dict(proposal.validation_summary or {})
    validation_summary["nutrition_solver"] = {
        "version": SOLVER_MEAL_PROPOSAL_VERSION,
        "status": optimization_result.status.value,
        "target": target.as_dict(),
        "result": optimization_result.as_dict(),
        "candidate_preview": {
            "count": candidates_result.count,
            "returned_count": candidates_result.count,
            "total_eligible_count": candidates_result.total_eligible_count,
            "active_visible_count": candidates_result.active_visible_count,
            "excluded_solver_disabled_count": candidates_result.excluded_solver_disabled_count,
            "has_more": candidates_result.total_eligible_count > candidates_result.count,
            "readiness": candidates_result.as_dict()["readiness"],
            "limit": candidates_result.limit,
            "search": candidates_result.search,
            "include_extended": candidates_result.include_extended,
        },
        "source_boundary": {
            "candidate_source": "notas.Food",
            "candidate_contract": "nutrition_solver.domain.models.SolverFood",
            "catalog_fields_exposed": False,
            "external_payloads_exposed": False,
            "applies_changes": False,
            "requires_human_review": True,
        },
        "culinary_primary": dict(culinary_readiness or {}),
        "raw_food_fallback_used": True,
    }
    proposal.validation_summary = validation_summary
    proposal.save(update_fields=["validation_summary"])


def _build_summary(*, summary: str, optimization_result) -> str:
    clean_summary = (summary or "").strip()
    assessment = optimization_result.diagnostics.assessment
    reason_code = assessment.reason_code if assessment else "unknown"
    solver_summary = (
        f"Propuesta generada por Nutrition Solver. "
        f"Estado: {optimization_result.status.value}. Motivo: {reason_code}."
    )

    if clean_summary:
        return f"{clean_summary} · {solver_summary}"

    return solver_summary


def _normalize_title(title: str) -> str:
    clean_title = (title or "").strip()
    if not clean_title:
        raise ValueError("nutrition_solver_meal_title_required")
    return clean_title


def _normalize_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        return DEFAULT_SOLVER_MEAL_CANDIDATE_LIMIT
    if limit <= 0:
        return DEFAULT_SOLVER_MEAL_CANDIDATE_LIMIT
    return min(limit, DEFAULT_SOLVER_FOOD_CANDIDATE_LIMIT)
