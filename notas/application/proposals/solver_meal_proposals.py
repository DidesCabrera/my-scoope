from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from django.db import transaction

from nutrition_solver.application.contracts import (
    OptimizationInput,
    OptimizationStatus,
    SolverConstraint,
    optimize_meal_portions,
)
from nutrition_solver.domain.models import MacroTarget

from notas.application.dto.proposal_payloads import CREATE_MEAL_INTENT
from notas.application.queries.solver_food_candidates import (
    DEFAULT_SOLVER_FOOD_CANDIDATE_LIMIT,
    list_solver_food_candidates,
)
from notas.application.services.commands.proposal_commands import (
    NutritionProposalCreateResult,
    create_validated_meal_proposal,
)
from notas.domain.models import NutritionProposal


SOLVER_MEAL_PROPOSAL_VERSION = "nutrition_solver_meal_proposal_v1"
DEFAULT_SOLVER_MEAL_CANDIDATE_LIMIT = 40


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
    candidates_result = list_solver_food_candidates(
        user,
        search=search,
        limit=_normalize_limit(limit),
        include_extended=include_extended,
    )
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
    )

    return SolverMealProposalResult(
        proposal=proposal_result.proposal,
        optimization_result=optimization_result,
        candidate_count=candidates_result.count,
    )


def _parse_macro_target(target: Mapping[str, Any]) -> MacroTarget:
    if not isinstance(target, Mapping):
        raise ValueError("nutrition_solver_target_must_be_object")

    kcal = _required_positive_float(target, "kcal", aliases=("total_kcal", "calories"))
    protein = _required_positive_float(target, "protein", aliases=("protein_g",))
    carbs = _required_positive_float(target, "carbs", aliases=("carbs_g", "carbohydrates"))
    fat = _required_positive_float(target, "fat", aliases=("fat_g",))

    return MacroTarget(
        kcal=kcal,
        protein=protein,
        carbs=carbs,
        fat=fat,
    )


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


def _build_create_meal_payload(*, meal_name: str, optimization_result) -> dict:
    return {
        "intent": CREATE_MEAL_INTENT,
        "meal": {
            "name": meal_name,
            "foods": [
                {
                    "food_id": int(portion.food_id),
                    "quantity": round(float(portion.quantity_g), 2),
                    "unit": "g",
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
