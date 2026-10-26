"""Build two reviewable onboarding minutas from curated Explore plans."""

from __future__ import annotations

import unicodedata
from dataclasses import replace

from django.db import transaction
from django.db.models import Prefetch

from notas.application.ai_intake.optimizer_v2_adapter import _expanded_allergen_terms
from notas.application.dto.proposal_payloads import (
    CREATE_DAILYPLAN_INTENT,
    ProposedDailyPlanDTO,
    ProposedDailyPlanMealDTO,
    ProposedDailyPlanPayloadDTO,
    ProposedFoodItemDTO,
    ProposedMealDTO,
)
from notas.application.queries.proposal_simulation_queries import simulate_proposal_payload
from notas.application.queries.solver_food_candidates import build_solver_food_candidate
from notas.application.validation.proposal_payload_validators import validate_proposal_payload_or_raise
from notas.domain.models import (
    DailyPlanCatalogEntry,
    DailyPlanMeal,
    MealFood,
    NutritionProposal,
    NutritionProposalAuditEvent,
)
from nutrition_solver.application.portion_solver import PortionSolverError, solve_meal_portions
from nutrition_solver.application.validators import PortionValidationInput, validate_generated_dailyplan
from nutrition_solver.domain.models import MacroTarget, PortionBounds

_COMPATIBLE_STYLES = {
    "omnivore": ("omnivore", "pescatarian", "vegetarian", "vegan"),
    "pescatarian": ("pescatarian", "vegetarian", "vegan"),
    "vegetarian": ("vegetarian", "vegan"),
    "vegan": ("vegan",),
    "flexitarian": ("vegetarian", "omnivore", "pescatarian", "vegan"),
}
_KEY_ROLES = {"protein", "carb", "fat", "balanced"}
_ROLE_MAXIMUM_G = {"protein": 350, "carb": 420, "fat": 120, "balanced": 500}
_DIETARY_TAGS = {
    "pescatarian": {"pescatarian", "pescetariano", "pescetariana", "vegetarian", "vegetariano", "vegetariana", "vegan", "vegano", "vegana"},
    "vegetarian": {"vegetarian", "vegetariano", "vegetariana", "vegan", "vegano", "vegana"},
    "vegan": {"vegan", "vegano", "vegana"},
}


def _normalized(value: str) -> str:
    plain = unicodedata.normalize("NFKD", str(value or "").casefold())
    return " ".join("".join(char for char in plain if not unicodedata.combining(char)).split())


def _catalog_candidates(pattern: str):
    styles = _COMPATIBLE_STYLES.get(pattern)
    if styles is None:
        raise ValueError("onboarding_dietary_pattern_invalid")
    rows = DailyPlanCatalogEntry.objects.filter(
        is_published=True,
        dietary_style__in=styles,
        dailyplan__is_draft=False,
    ).select_related("dailyplan").prefetch_related(Prefetch(
        "dailyplan__dailyplan_meals",
        queryset=DailyPlanMeal.objects.select_related("meal").prefetch_related(Prefetch(
            "meal__meal_food_set",
            queryset=MealFood.objects.select_related("food").order_by("order", "id"),
        )).order_by("order", "id"),
    ))
    return sorted(rows, key=lambda row: (styles.index(row.dietary_style), row.sort_order, row.pk))


def _food_allowed(food, *, pattern: str, exclusions: set[str], allergens: set[str]) -> bool:
    if not food.is_active or not (food.is_global or food.created_by_id is None):
        return False
    label = _normalized(f"{food.name} {food.canonical_name}")
    if any(term in label for term in exclusions):
        return False
    values = (food.solver_capabilities or {}).get("values") or {}
    accepted_tags = _DIETARY_TAGS.get(pattern)
    if accepted_tags is not None:
        tags = values.get("dietary_tags")
        if not isinstance(tags, list) or not accepted_tags.intersection(_normalized(tag) for tag in tags):
            return False
    if allergens:
        declared = values.get("allergens")
        if not isinstance(declared, list):
            return False  # Unknown allergen data cannot prove compatibility.
        if allergens.intersection(_normalized(value) for value in declared):
            return False
    return True


def _candidate_payload(entry, *, pattern: str, target: MacroTarget, exclusions: set[str], allergens: set[str]):
    slots = list(entry.dailyplan.dailyplan_meals.all())
    if not slots:
        return None
    solver_foods, items, bounds_by_id = [], {}, {}
    for slot in slots:
        meal_foods = list(slot.meal.meal_food_set.all())
        if not meal_foods:
            return None
        for item in meal_foods:
            food = item.food
            base = float(item.quantity)
            if base <= 0 or food.portion_unit != "g" or not _food_allowed(food, pattern=pattern, exclusions=exclusions, allergens=allergens):
                return None
            candidate = build_solver_food_candidate(food)
            if candidate.role in _KEY_ROLES:
                minimum = max(1, base * 0.5, float(food.min_portion_g or 0))
                maximum = min(base * 2.2, _ROLE_MAXIMUM_G[candidate.role], float(food.max_portion_g or base * 2.2))
                if minimum > base or maximum < base:
                    return None
            else:
                minimum = maximum = base
            solver_foods.append(replace(candidate, food_id=item.pk, bounds=PortionBounds(minimum, maximum, 1)))
            items[item.pk] = item
            bounds_by_id[item.pk] = (candidate.role, minimum, maximum)
    try:
        solved = solve_meal_portions(foods=solver_foods, target=target)
    except PortionSolverError:
        return None
    quantities = {portion.food_id: portion.quantity_g for portion in solved.portions}
    if set(quantities) != set(items):
        return None
    meals = []
    for slot in slots:
        foods = [ProposedFoodItemDTO(
            food_id=item.food_id, quantity=round(quantities[item.pk], 2), unit="g",
        ) for item in slot.meal.meal_food_set.all()]
        meals.append(ProposedDailyPlanMealDTO(
            hour=slot.hour.strftime("%H:%M") if slot.hour else None,
            note=slot.note or "",
            meal=ProposedMealDTO(name=slot.meal.name, foods=foods),
        ))
    payload = ProposedDailyPlanPayloadDTO(
        intent=CREATE_DAILYPLAN_INTENT,
        dailyplan=ProposedDailyPlanDTO(name=entry.dailyplan.name, meals=meals),
    ).as_dict()
    validate_proposal_payload_or_raise(payload)
    portions = [PortionValidationInput(
        food_id=item.food_id,
        food_name=item.food.name,
        quantity_g=quantities[item_id],
        role=bounds_by_id[item_id][0],
        minimum_g=bounds_by_id[item_id][1],
        maximum_g=bounds_by_id[item_id][2],
    ) for item_id, item in items.items()]
    return payload, portions, solved.diagnostics.as_dict(), {
        str(item_id): {"from_g": round(item.quantity, 2), "to_g": round(quantities[item_id], 2)}
        for item_id, item in items.items() if abs(item.quantity - quantities[item_id]) >= 0.5
    }


@transaction.atomic
def generate_onboarding_catalog_minutas(*, user, estimate: dict, preferences: dict) -> tuple[NutritionProposal, NutritionProposal]:
    pattern = str(preferences.get("dietary_pattern") or "")
    exclusions = {_normalized(value) for value in preferences.get("avoided_foods") or [] if _normalized(value)}
    allergens = _expanded_allergen_terms(preferences.get("allergies_or_intolerances") or [])
    target = MacroTarget(
        kcal=float(estimate["total_kcal"]), protein=float(estimate["protein"]),
        carbs=float(estimate["carbs"]), fat=float(estimate["fat"]),
    )
    proposals = []
    for entry in _catalog_candidates(pattern):
        candidate = _candidate_payload(entry, pattern=pattern, target=target, exclusions=exclusions, allergens=allergens)
        if candidate is None:
            continue
        payload, portions, diagnostics, adjustments = candidate
        simulation = simulate_proposal_payload(user=user, payload=payload).as_dict()
        result = simulation["dailyplan"]
        kpis = result["kpis"]
        actual = MacroTarget(kcal=kpis["total_kcal"], protein=kpis["protein"], carbs=kpis["carbs"], fat=kpis["fat"])
        validation = validate_generated_dailyplan(
            target=target, actual=actual, expected_meals_count=len(payload["dailyplan"]["meals"]),
            actual_meals_count=len(result["meals"]), excluded_terms=exclusions, portions=portions,
        )
        if not validation.is_valid:
            continue
        proposal = NutritionProposal.objects.create(
            created_by=user, source=NutritionProposal.SOURCE_SYSTEM,
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            title=entry.dailyplan.name, summary=f"Minuta adaptada desde Explorar · {entry.get_dietary_style_display()}.",
            targets=target.as_dict(), proposed_payload=payload,
            current_snapshot={"source": "onboarding_catalog_minuta.v1", "catalog_entry_id": entry.pk,
                              "source_dailyplan_id": entry.dailyplan_id, "adjustments_g": adjustments,
                              "solver_diagnostics": diagnostics},
            validation_summary={"payload_validation": {"is_valid": True, "intent": CREATE_DAILYPLAN_INTENT},
                                "simulation": simulation, "engine_validation": validation.as_dict(),
                                "requires_human_review": True},
        )
        NutritionProposalAuditEvent.objects.create(
            proposal=proposal, actor=user, action=NutritionProposalAuditEvent.ACTION_CREATED,
            status_before="", status_after=proposal.status,
            message="Onboarding catalog minuta adapted for nutrition targets.",
            metadata={"catalog_entry_id": entry.pk, "intent": CREATE_DAILYPLAN_INTENT},
        )
        proposals.append(proposal)
        if len(proposals) == 2:
            return proposals[0], proposals[1]
    raise ValueError("onboarding_catalog_two_valid_minutas_unavailable")
