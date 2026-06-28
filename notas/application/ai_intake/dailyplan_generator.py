from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.db import transaction
from django.db.models import Q

from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    deserialize_brief,
)
from notas.application.ai_intake.proposal_from_brief import (
    AI_INTAKE_SOURCE,
    AI_NUTRITION_BRIEF_INTENT,
)
from notas.application.dto.proposal_payloads import (
    CREATE_DAILYPLAN_INTENT,
    ProposedDailyPlanDTO,
    ProposedDailyPlanMealDTO,
    ProposedDailyPlanPayloadDTO,
    ProposedFoodItemDTO,
    ProposedMealDTO,
)
from notas.application.queries.proposal_simulation_queries import (
    simulate_proposal_payload,
)
from notas.application.queries.read_boundaries import get_readable_food_queryset
from notas.application.validation.proposal_payload_validators import (
    validate_proposal_payload_or_raise,
)
from notas.domain.constants.nutrition import (
    CARBS_KCAL_PER_GRAM,
    FAT_KCAL_PER_GRAM,
    PROTEIN_KCAL_PER_GRAM,
)
from notas.domain.models import (
    NutritionProposal,
    NutritionProposalAuditEvent,
)


DAILYPLAN_GENERATOR_INTENT = CREATE_DAILYPLAN_INTENT
DAILYPLAN_GENERATOR_VERSION = "rules_v1"

DEFAULT_CALORIE_TARGET = 2200
DEFAULT_PROTEIN_TARGET = 140
DEFAULT_MEALS_PER_DAY = 4

MEAL_HOURS = {
    1: ["13:00"],
    2: ["13:00", "20:00"],
    3: ["10:00", "14:00", "20:00"],
    4: ["09:00", "13:00", "17:00", "21:00"],
    5: ["08:00", "11:00", "14:00", "17:00", "21:00"],
    6: ["08:00", "10:30", "13:00", "16:00", "19:00", "21:30"],
}

MEAL_LABELS = {
    1: ["Comida principal"],
    2: ["Comida 1", "Comida 2"],
    3: ["Desayuno", "Almuerzo", "Cena"],
    4: ["Desayuno", "Almuerzo", "Snack", "Cena"],
    5: ["Desayuno", "Media mañana", "Almuerzo", "Snack", "Cena"],
    6: ["Desayuno", "Media mañana", "Almuerzo", "Snack", "Cena", "Colación"],
}

PROTEIN_KEYWORDS = (
    "pollo",
    "huevo",
    "huevos",
    "atun",
    "atún",
    "pescado",
    "carne",
    "pavo",
    "yogur",
    "yogurt",
    "quesillo",
)

CARB_KEYWORDS = (
    "arroz",
    "avena",
    "quinoa",
    "papa",
    "camote",
    "pan",
    "pasta",
    "lentejas",
    "porotos",
    "garbanzos",
    "platano",
    "plátano",
)

FAT_KEYWORDS = (
    "palta",
    "nuez",
    "nueces",
    "mani",
    "maní",
    "aceite",
    "almendra",
)

VEG_KEYWORDS = (
    "tomate",
    "lechuga",
    "zanahoria",
    "brocoli",
    "brócoli",
    "espinaca",
    "pepino",
)


@dataclass(frozen=True)
class DailyPlanGeneratorFood:
    food_id: int
    name: str
    protein: float
    carbs: float
    fat: float
    kcal_per_100g: float


@dataclass(frozen=True)
class GeneratedDailyPlanProposalResult:
    source_proposal: NutritionProposal
    proposal: NutritionProposal


class DailyPlanGeneratorError(ValueError):
    pass


def generate_dailyplan_proposal_from_brief_proposal(
    *,
    user,
    source_proposal: NutritionProposal,
) -> GeneratedDailyPlanProposalResult:
    """Create a concrete create_dailyplan proposal from an AI NutritionBrief.

    Patch 4 intentionally keeps the generator deterministic and conservative:
    it uses readable foods, simple meal templates and validation/simulation, but
    it does not create DailyPlans, Meals or MealFoods. The generated artifact is
    still a reviewable NutritionProposal that the user can inspect and apply.
    """
    _ensure_can_generate_from_source(
        user=user,
        source_proposal=source_proposal,
    )

    brief = _extract_brief(source_proposal)

    if brief.requested_entity != "daily_plan":
        raise DailyPlanGeneratorError("dailyplan_generator_only_supports_daily_plan_briefs")

    payload = build_dailyplan_payload_from_brief(
        user=user,
        brief=brief,
    )

    validate_proposal_payload_or_raise(payload)
    simulation = simulate_proposal_payload(
        user=user,
        payload=payload,
    )

    targets = _build_targets(brief)
    validation_summary = _build_validation_summary(
        brief=brief,
        simulation=simulation.as_dict(),
    )
    title = _build_generated_proposal_title(brief)
    summary = _build_generated_proposal_summary(brief)

    with transaction.atomic():
        proposal = NutritionProposal.objects.create(
            dailyplan=None,
            created_by=user,
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            source=NutritionProposal.SOURCE_AI,
            title=title,
            summary=summary,
            targets=targets,
            current_snapshot={
                "source": AI_INTAKE_SOURCE,
                "kind": "generated_dailyplan_from_nutrition_brief",
                "source_proposal_id": source_proposal.id,
                "generator_version": DAILYPLAN_GENERATOR_VERSION,
            },
            proposed_payload=payload,
            validation_summary=validation_summary,
        )

        NutritionProposalAuditEvent.objects.create(
            proposal=proposal,
            actor=user,
            action=NutritionProposalAuditEvent.ACTION_CREATED,
            status_before="",
            status_after=proposal.status,
            message="Create DailyPlan proposal generated from AI NutritionBrief.",
            metadata={
                "source": AI_INTAKE_SOURCE,
                "source_proposal_id": source_proposal.id,
                "generator_version": DAILYPLAN_GENERATOR_VERSION,
                "intent": CREATE_DAILYPLAN_INTENT,
            },
        )

    return GeneratedDailyPlanProposalResult(
        source_proposal=source_proposal,
        proposal=proposal,
    )


def build_dailyplan_payload_from_brief(
    *,
    user,
    brief: NutritionBrief,
) -> dict:
    foods = _load_foods_for_generation(user)

    if len(foods) < 3:
        raise DailyPlanGeneratorError("dailyplan_generator_requires_at_least_three_readable_foods")

    excluded_terms = _normalize_terms(brief.excluded_foods)
    preferred_terms = _normalize_terms(brief.preferred_foods)
    meals_per_day = _normalize_meals_per_day(brief.meals_per_day)
    target_kcal = brief.calorie_target or DEFAULT_CALORIE_TARGET
    target_protein = brief.protein_target or DEFAULT_PROTEIN_TARGET

    labels = MEAL_LABELS.get(meals_per_day, MEAL_LABELS[DEFAULT_MEALS_PER_DAY])
    hours = MEAL_HOURS.get(meals_per_day, MEAL_HOURS[DEFAULT_MEALS_PER_DAY])

    generated_meals = []

    for index in range(meals_per_day):
        label = labels[index]
        is_snack = _is_snack_label(label)
        meal_target_kcal = target_kcal / meals_per_day
        meal_target_protein = target_protein / meals_per_day
        meal = _build_meal(
            index=index,
            label=label,
            foods=foods,
            excluded_terms=excluded_terms,
            preferred_terms=preferred_terms,
            meal_target_kcal=meal_target_kcal,
            meal_target_protein=meal_target_protein,
            is_snack=is_snack,
        )
        generated_meals.append(
            ProposedDailyPlanMealDTO(
                hour=hours[index],
                note=_build_meal_note(
                    label=label,
                    is_snack=is_snack,
                ),
                meal=meal,
            )
        )

    dailyplan = ProposedDailyPlanDTO(
        name=_build_dailyplan_name(brief),
        meals=generated_meals,
    )

    return ProposedDailyPlanPayloadDTO(
        intent=CREATE_DAILYPLAN_INTENT,
        dailyplan=dailyplan,
    ).as_dict()


def _ensure_can_generate_from_source(
    *,
    user,
    source_proposal: NutritionProposal,
) -> None:
    if source_proposal.created_by_id != user.id:
        raise DailyPlanGeneratorError("dailyplan_generator_not_allowed")

    payload = source_proposal.proposed_payload or {}

    if not isinstance(payload, dict):
        raise DailyPlanGeneratorError("dailyplan_generator_source_payload_invalid")

    if payload.get("intent") != AI_NUTRITION_BRIEF_INTENT:
        raise DailyPlanGeneratorError("dailyplan_generator_source_must_be_nutrition_brief")

    if source_proposal.status not in {
        NutritionProposal.STATUS_PENDING_REVIEW,
        NutritionProposal.STATUS_APPROVED,
    }:
        raise DailyPlanGeneratorError("dailyplan_generator_source_not_active")


def _extract_brief(source_proposal: NutritionProposal) -> NutritionBrief:
    payload = source_proposal.proposed_payload or {}

    if not isinstance(payload, dict):
        raise DailyPlanGeneratorError("dailyplan_generator_source_payload_invalid")

    brief = deserialize_brief(payload.get("nutrition_brief"))

    if brief is None:
        raise DailyPlanGeneratorError("dailyplan_generator_brief_not_found")

    return brief


def _load_foods_for_generation(user) -> list[DailyPlanGeneratorFood]:
    queryset = (
        get_readable_food_queryset(user)
        .filter(is_active=True)
        .order_by("-is_verified", "name", "id")
    )

    foods = []

    for food in queryset[:250]:
        protein = float(food.protein)
        carbs = float(food.carbs)
        fat = float(food.fat)
        kcal = (
            protein * PROTEIN_KCAL_PER_GRAM
            + carbs * CARBS_KCAL_PER_GRAM
            + fat * FAT_KCAL_PER_GRAM
        )

        if kcal <= 0:
            continue

        foods.append(
            DailyPlanGeneratorFood(
                food_id=food.id,
                name=food.name,
                protein=protein,
                carbs=carbs,
                fat=fat,
                kcal_per_100g=kcal,
            )
        )

    return foods


def _build_meal(
    *,
    index: int,
    label: str,
    foods: list[DailyPlanGeneratorFood],
    excluded_terms: list[str],
    preferred_terms: list[str],
    meal_target_kcal: float,
    meal_target_protein: float,
    is_snack: bool,
) -> ProposedMealDTO:
    protein_food = _pick_food(
        foods=foods,
        preferred_terms=preferred_terms,
        excluded_terms=excluded_terms,
        keywords=PROTEIN_KEYWORDS,
        sort_key=lambda food: (food.protein, food.kcal_per_100g),
    )
    carb_food = _pick_food(
        foods=foods,
        preferred_terms=preferred_terms,
        excluded_terms=excluded_terms,
        keywords=CARB_KEYWORDS,
        sort_key=lambda food: (food.carbs, food.kcal_per_100g),
        avoid_ids={protein_food.food_id},
    )
    fat_food = _pick_food(
        foods=foods,
        preferred_terms=preferred_terms,
        excluded_terms=excluded_terms,
        keywords=FAT_KEYWORDS,
        sort_key=lambda food: (food.fat, food.kcal_per_100g),
        avoid_ids={protein_food.food_id, carb_food.food_id},
        required=False,
    )
    veg_food = _pick_food(
        foods=foods,
        preferred_terms=[],
        excluded_terms=excluded_terms,
        keywords=VEG_KEYWORDS,
        sort_key=lambda food: (-(food.kcal_per_100g), food.carbs),
        avoid_ids={protein_food.food_id, carb_food.food_id, fat_food.food_id if fat_food else 0},
        required=False,
    )

    proposed_foods = []
    protein_quantity = _protein_quantity(
        protein_food=protein_food,
        meal_target_protein=meal_target_protein,
        is_snack=is_snack,
    )
    carb_quantity = _carb_quantity(
        carb_food=carb_food,
        meal_target_kcal=meal_target_kcal,
        is_snack=is_snack,
    )

    proposed_foods.append(
        ProposedFoodItemDTO(
            food_id=protein_food.food_id,
            quantity=protein_quantity,
        )
    )
    proposed_foods.append(
        ProposedFoodItemDTO(
            food_id=carb_food.food_id,
            quantity=carb_quantity,
        )
    )

    if fat_food:
        proposed_foods.append(
            ProposedFoodItemDTO(
                food_id=fat_food.food_id,
                quantity=15 if is_snack else 25,
            )
        )

    if veg_food and not is_snack:
        proposed_foods.append(
            ProposedFoodItemDTO(
                food_id=veg_food.food_id,
                quantity=100,
            )
        )

    return ProposedMealDTO(
        name=f"{label} IA {index + 1}",
        foods=proposed_foods,
    )


def _pick_food(
    *,
    foods: list[DailyPlanGeneratorFood],
    preferred_terms: list[str],
    excluded_terms: list[str],
    keywords: Iterable[str],
    sort_key,
    avoid_ids: set[int] | None = None,
    required: bool = True,
) -> DailyPlanGeneratorFood | None:
    avoid_ids = avoid_ids or set()
    candidate_groups = [
        preferred_terms,
        list(keywords),
        [],
    ]

    for terms in candidate_groups:
        candidates = [
            food
            for food in foods
            if food.food_id not in avoid_ids
            and not _matches_any(food.name, excluded_terms)
            and (not terms or _matches_any(food.name, terms))
        ]

        if not candidates:
            continue

        candidates.sort(
            key=sort_key,
            reverse=True,
        )
        return candidates[0]

    if required:
        raise DailyPlanGeneratorError("dailyplan_generator_food_candidates_not_found")

    return None


def _protein_quantity(
    *,
    protein_food: DailyPlanGeneratorFood,
    meal_target_protein: float,
    is_snack: bool,
) -> float:
    if protein_food.protein <= 0:
        return 120.0 if is_snack else 160.0

    quantity = (meal_target_protein / protein_food.protein) * 100
    minimum = 80 if is_snack else 100
    maximum = 220 if is_snack else 260
    return _round_to_five(_clamp(quantity, minimum, maximum))


def _carb_quantity(
    *,
    carb_food: DailyPlanGeneratorFood,
    meal_target_kcal: float,
    is_snack: bool,
) -> float:
    if carb_food.kcal_per_100g <= 0:
        return 60.0 if is_snack else 120.0

    kcal_share = meal_target_kcal * (0.35 if is_snack else 0.45)
    quantity = (kcal_share / carb_food.kcal_per_100g) * 100
    minimum = 30 if is_snack else 60
    maximum = 120 if is_snack else 220
    return _round_to_five(_clamp(quantity, minimum, maximum))


def _normalize_meals_per_day(value: int | None) -> int:
    if value is None:
        return DEFAULT_MEALS_PER_DAY

    return max(1, min(int(value), 6))


def _build_dailyplan_name(brief: NutritionBrief) -> str:
    goal_label = brief.goal_label if brief.goal else "objetivo nutricional"
    return f"Plan IA - {goal_label}"


def _build_meal_note(
    *,
    label: str,
    is_snack: bool,
) -> str:
    if is_snack:
        return "Propuesta simple generada desde brief; ajustar por preferencias antes de aplicar."

    return f"{label} generado desde brief; validar porciones antes de aplicar."


def _build_targets(brief: NutritionBrief) -> dict:
    targets = {}

    if brief.calorie_target is not None:
        targets["total_kcal"] = brief.calorie_target

    if brief.protein_target is not None:
        targets["protein"] = brief.protein_target

    if brief.carb_target is not None:
        targets["carbs"] = brief.carb_target

    if brief.fat_target is not None:
        targets["fat"] = brief.fat_target

    return targets


def _build_validation_summary(
    *,
    brief: NutritionBrief,
    simulation: dict,
) -> dict:
    dailyplan = simulation.get("dailyplan") or {}
    kpis = dailyplan.get("kpis") or {}

    return {
        "payload_validation": {
            "is_valid": True,
            "intent": CREATE_DAILYPLAN_INTENT,
        },
        "simulation": simulation,
        "generator": {
            "version": DAILYPLAN_GENERATOR_VERSION,
            "strategy": "simple_rules_without_solver",
            "source_intent": AI_NUTRITION_BRIEF_INTENT,
            "notes": [
                "Generador heurístico inicial: selecciona alimentos legibles y porciones razonables.",
                "No usa solver de optimización avanzada todavía.",
                "La propuesta debe revisarse antes de aplicar el DailyPlan final.",
            ],
        },
        "target_comparison": _build_target_comparison(
            targets=_build_targets(brief),
            kpis=kpis,
        ),
    }


def _build_target_comparison(
    *,
    targets: dict,
    kpis: dict,
) -> dict:
    comparison = {}
    metric_map = {
        "total_kcal": "total_kcal",
        "protein": "protein",
        "carbs": "carbs",
        "fat": "fat",
    }

    for target_key, kpi_key in metric_map.items():
        target = targets.get(target_key)
        actual = kpis.get(kpi_key)

        if target is None or actual is None:
            continue

        diff = float(actual) - float(target)
        comparison[target_key] = {
            "target": float(target),
            "actual": round(float(actual), 2),
            "diff": round(diff, 2),
            "diff_percent": round((diff / float(target)) * 100, 2) if float(target) else None,
        }

    return comparison


def _build_generated_proposal_title(brief: NutritionBrief) -> str:
    return f"DailyPlan IA - {brief.goal_label if brief.goal else 'Primer plan'}"


def _build_generated_proposal_summary(brief: NutritionBrief) -> str:
    pieces = [
        "Propuesta concreta generada desde NutritionBrief.",
        f"Objetivo: {brief.goal_label}.",
        f"Comidas: {_normalize_meals_per_day(brief.meals_per_day)}.",
    ]

    if brief.style_preferences:
        pieces.append(f"Estilo: {', '.join(brief.style_preferences)}.")

    if brief.excluded_foods:
        pieces.append(f"Excluye: {', '.join(brief.excluded_foods)}.")

    pieces.append("Generador inicial por reglas; no usa solver avanzado todavía.")
    return " ".join(pieces)


def _normalize_terms(values: Iterable[str]) -> list[str]:
    return [
        _normalize_text(value)
        for value in values
        if _normalize_text(value)
    ]


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _matches_any(text: str, terms: Iterable[str]) -> bool:
    normalized = _normalize_text(text)
    return any(term and term in normalized for term in terms)


def _is_snack_label(label: str) -> bool:
    normalized = _normalize_text(label)
    return normalized in {"snack", "media mañana", "colación", "colacion"}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(float(value), maximum))


def _round_to_five(value: float) -> float:
    return float(round(value / 5) * 5)
