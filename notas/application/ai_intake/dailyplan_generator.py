from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Iterable

from django.conf import settings
from django.db import transaction

from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    apply_subject_context,
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
from notas.application.services.nutrition.weight import get_current_weight
from notas.application.validation.proposal_payload_validators import (
    validate_proposal_payload_or_raise,
)
from notas.domain.constants.nutrition import (
    CARBS_KCAL_PER_GRAM,
    FAT_KCAL_PER_GRAM,
    PROTEIN_KCAL_PER_GRAM,
)
from notas.application.nutrition_engine.candidate_selector import (
    CandidateSelectionError,
    NutritionFoodCandidate,
    select_meal_food_candidates,
)
from notas.application.nutrition_engine.meal_templates import (
    MealRoleTemplate,
    MealTemplate,
    build_dailyplan_meal_templates,
    normalize_meals_per_day as normalize_template_meals_per_day,
)
from nutrition_solver.domain.models import (
    MacroTarget,
    PortionBounds,
    SolverFood,
)
from notas.application.ai_intake.optimizer_v2_adapter import (
    DailyPlanOptimizerV2Error,
    build_shadow_summary_for_legacy_generator,
    run_dailyplan_optimizer_v2,
)
from nutrition_solver.application.portion_solver import solve_meal_portions
from notas.application.nutrition_engine.target_estimator import (
    DailyNutritionTargetPlan,
    TargetEstimationProfile,
    estimate_daily_targets,
)
from nutrition_solver.application.validators import (
    PortionValidationInput,
    compare_macro_targets,
    validate_generated_dailyplan,
)
from notas.domain.models import (
    NutritionProposal,
    NutritionProposalAuditEvent,
)


DAILYPLAN_GENERATOR_INTENT = CREATE_DAILYPLAN_INTENT
DAILYPLAN_GENERATOR_VERSION = "nutrition_engine_v7_optimizer_gate"

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

MEAL_KCAL_ALLOCATION = {
    1: [1.0],
    2: [0.48, 0.52],
    3: [0.28, 0.38, 0.34],
    4: [0.24, 0.34, 0.16, 0.26],
    5: [0.22, 0.12, 0.32, 0.14, 0.20],
    6: [0.20, 0.10, 0.30, 0.12, 0.20, 0.08],
}

PROTEIN_KEYWORDS = (
    "pollo",
    "huevo",
    "huevos",
    "atun",
    "atún",
    "pescado",
    "carne",
    "vacuno",
    "pavo",
    "cerdo",
    "yogur",
    "yogurt",
    "quesillo",
    "queso cottage",
    "proteina",
    "proteína",
)

CARB_KEYWORDS = (
    "arroz",
    "avena",
    "quinoa",
    "papa",
    "camote",
    "pan",
    "pasta",
    "fideos",
    "lentejas",
    "porotos",
    "garbanzos",
    "platano",
    "plátano",
    "fruta",
    "manzana",
    "berries",
    "arandanos",
    "arándanos",
)

FAT_KEYWORDS = (
    "palta",
    "nuez",
    "nueces",
    "mani",
    "maní",
    "aceite",
    "almendra",
    "almendras",
    "mantequilla de mani",
    "mantequilla de maní",
)

VEG_KEYWORDS = (
    "tomate",
    "lechuga",
    "zanahoria",
    "brocoli",
    "brócoli",
    "espinaca",
    "pepino",
    "zapallo italiano",
    "verdura",
    "vegetal",
)

PROTEIN_GROUP_KEYWORDS = (
    "meat",
    "poultry",
    "fish",
    "seafood",
    "egg",
    "dairy",
    "proteins",
    "carnes",
    "aves",
    "pescados",
    "huevos",
    "lacteos",
    "lácteos",
)

CARB_GROUP_KEYWORDS = (
    "grain",
    "cereal",
    "starch",
    "legume",
    "fruit",
    "granos",
    "cereales",
    "tuberculos",
    "tubérculos",
    "legumbres",
    "frutas",
)

FAT_GROUP_KEYWORDS = (
    "fat",
    "oil",
    "nuts",
    "seed",
    "grasas",
    "aceites",
    "frutos secos",
    "semillas",
)

VEG_GROUP_KEYWORDS = (
    "vegetable",
    "vegetables",
    "verduras",
    "hortalizas",
)


@dataclass(frozen=True)
class DailyPlanGeneratorFood:
    food_id: int
    name: str
    protein: float
    carbs: float
    fat: float
    kcal_per_100g: float
    food_group: str = ""
    food_subgroup: str = ""
    default_portion_g: float | None = None
    min_portion_g: float | None = None
    max_portion_g: float | None = None
    portion_step_g: float | None = None
    data_quality_score: int = 0
    is_verified: bool = False


@dataclass(frozen=True)
class GeneratedDailyPlanProposalResult:
    source_proposal: NutritionProposal
    proposal: NutritionProposal


DailyPlanTargetPlan = DailyNutritionTargetPlan


@dataclass(frozen=True)
class MealTarget:
    kcal: float
    protein: float
    carbs: float
    fat: float

    def as_macro_target(self) -> MacroTarget:
        return MacroTarget(
            kcal=self.kcal,
            protein=self.protein,
            carbs=self.carbs,
            fat=self.fat,
        )


class DailyPlanGeneratorError(ValueError):
    pass


def generate_dailyplan_proposal_from_brief_proposal(
    *,
    user,
    source_proposal: NutritionProposal,
    source: str = NutritionProposal.SOURCE_AI,
) -> GeneratedDailyPlanProposalResult:
    """Create a concrete create_dailyplan proposal from an AI NutritionBrief.

    Patch 5 keeps the generator deterministic and conservative, but improves
    the quality of the first concrete proposal: targets are estimated when the
    brief is incomplete, food matching uses category/quality signals, portions
    are tied to meal-level macro targets, and validation stores an explicit
    target comparison for review.
    """
    _ensure_can_generate_from_source(
        user=user,
        source_proposal=source_proposal,
    )

    brief = _extract_brief(source_proposal)

    if brief.requested_entity != "daily_plan":
        raise DailyPlanGeneratorError("dailyplan_generator_only_supports_daily_plan_briefs")

    brief = apply_subject_context(brief, user=user)
    target_plan = build_dailyplan_target_plan(
        user=user,
        brief=brief,
    )
    payload, solver_summary = _build_dailyplan_payload_with_solver_summary(
        user=user,
        brief=brief,
        target_plan=target_plan,
    )

    validate_proposal_payload_or_raise(payload)
    simulation = simulate_proposal_payload(
        user=user,
        payload=payload,
    )

    targets = _build_targets(target_plan)
    validation_summary = _build_validation_summary(
        brief=brief,
        target_plan=target_plan,
        simulation=simulation.as_dict(),
        solver_summary=solver_summary,
    )
    title = _build_generated_proposal_title(brief)
    summary = _build_generated_proposal_summary(
        brief=brief,
        target_plan=target_plan,
    )

    with transaction.atomic():
        proposal = NutritionProposal.objects.create(
            dailyplan=None,
            created_by=user,
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            source=source,
            title=title,
            summary=summary,
            targets=targets,
            current_snapshot={
                "source": AI_INTAKE_SOURCE,
                "kind": "generated_dailyplan_from_nutrition_brief",
                "source_proposal_id": source_proposal.id,
                "proposal_source": source,
                "generator_version": DAILYPLAN_GENERATOR_VERSION,
                "target_plan": target_plan.as_targets_dict(),
                "subject_context": _build_subject_context_snapshot(brief=brief, target_plan=target_plan),
                "nutrition_solver": solver_summary,
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
                "proposal_source": source,
                "source_proposal_id": source_proposal.id,
                "proposal_source": source,
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
    target_plan: DailyPlanTargetPlan | None = None,
) -> dict:
    payload, _solver_summary = _build_dailyplan_payload_with_solver_summary(
        user=user,
        brief=brief,
        target_plan=target_plan,
    )
    return payload


def _build_dailyplan_payload_with_solver_summary(
    *,
    user,
    brief: NutritionBrief,
    target_plan: DailyPlanTargetPlan | None = None,
) -> tuple[dict, dict]:
    target_plan = target_plan or build_dailyplan_target_plan(user=user, brief=brief)
    meals_per_day = _normalize_meals_per_day(brief.meals_per_day)
    backend = str(getattr(settings, "NUTRITION_SOLVER_BACKEND", "heuristic_v2")).strip().lower()
    shadow_enabled = bool(getattr(settings, "NUTRITION_SOLVER_SHADOW_ENABLED", False))
    shadow_backend = str(getattr(settings, "NUTRITION_SOLVER_SHADOW_BACKEND", "cp_sat_v1")).strip().lower()
    time_limit_ms = int(getattr(settings, "NUTRITION_SOLVER_TIME_LIMIT_MS", 1500))

    if backend == "cp_sat_v1":
        try:
            outcome = run_dailyplan_optimizer_v2(
                user=user,
                target_plan=target_plan,
                meals_per_day=meals_per_day,
                plan_name=_build_dailyplan_name(brief),
                excluded_terms=brief.excluded_foods,
                preferred_terms=brief.preferred_foods,
                backend=backend,
                shadow_enabled=shadow_enabled,
                shadow_backend=shadow_backend,
                time_limit_ms=time_limit_ms,
            )
        except DailyPlanOptimizerV2Error as exc:
            raise DailyPlanGeneratorError(str(exc)) from exc
        return outcome.payload, outcome.solver_summary

    if backend != "heuristic_v2":
        raise DailyPlanGeneratorError(f"dailyplan_generator_unknown_solver_backend:{backend}")

    payload = _build_legacy_dailyplan_payload_from_brief(
        user=user,
        brief=brief,
        target_plan=target_plan,
    )
    summary = {
        "contract_version": "nutrition_solver_optimization.v2",
        "active_backend": "legacy_generator_v6",
        "configured_backend": backend,
        "shadow_enabled": shadow_enabled,
    }
    if shadow_enabled:
        summary = build_shadow_summary_for_legacy_generator(
            user=user,
            target_plan=target_plan,
            meals_per_day=meals_per_day,
            excluded_terms=brief.excluded_foods,
            preferred_terms=brief.preferred_foods,
            shadow_backend=shadow_backend,
            time_limit_ms=time_limit_ms,
        )
    return payload, summary


def _build_legacy_dailyplan_payload_from_brief(
    *,
    user,
    brief: NutritionBrief,
    target_plan: DailyPlanTargetPlan,
) -> dict:
    foods = _load_foods_for_generation(user)

    if len(foods) < 3:
        raise DailyPlanGeneratorError("dailyplan_generator_requires_at_least_three_readable_foods")

    excluded_terms = _normalize_terms(brief.excluded_foods)
    preferred_terms = _normalize_terms(brief.preferred_foods)
    meals_per_day = _normalize_meals_per_day(brief.meals_per_day)

    templates = build_dailyplan_meal_templates(meals_per_day)

    generated_meals = []
    soft_avoid_ids: set[int] = set()

    for template in templates:
        meal_target = MealTarget(
            kcal=target_plan.total_kcal * template.kcal_allocation,
            protein=target_plan.protein * template.kcal_allocation,
            carbs=target_plan.carbs * template.kcal_allocation,
            fat=target_plan.fat * template.kcal_allocation,
        )
        meal = _build_meal(
            template=template,
            foods=foods,
            excluded_terms=excluded_terms,
            preferred_terms=preferred_terms,
            meal_target=meal_target,
            soft_avoid_ids=soft_avoid_ids,
        )
        soft_avoid_ids.update(food.food_id for food in meal.foods)
        generated_meals.append(
            ProposedDailyPlanMealDTO(
                hour=template.hour,
                note=_build_meal_note(
                    template=template,
                    target_plan=target_plan,
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


def build_dailyplan_target_plan(
    *,
    user,
    brief: NutritionBrief,
) -> DailyPlanTargetPlan:
    brief = apply_subject_context(brief, user=user)
    current_weight = brief.weight_kg if brief.weight_kg is not None else get_current_weight(user)
    profile = TargetEstimationProfile(
        goal=brief.goal,
        weight_kg=current_weight,
        height_cm=brief.height_cm,
        age_years=brief.age_years,
        sex=brief.sex,
        activity_level=brief.activity_level,
        energy_adjustment=brief.energy_adjustment,
        calorie_target=brief.calorie_target,
        protein_target=brief.protein_target,
        carb_target=brief.carb_target,
        fat_target=brief.fat_target,
        subject_source=brief.subject_source,
        ppk_weight_source=brief.ppk_weight_source,
        requires_library_ppk_warning=brief.requires_library_ppk_warning,
    )
    return estimate_daily_targets(profile)


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
        .order_by("-is_verified", "-data_quality_score", "name", "id")
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
                food_group=food.food_group or "",
                food_subgroup=food.food_subgroup or "",
                default_portion_g=_clean_optional_float(food.default_portion_g),
                min_portion_g=_clean_optional_float(food.min_portion_g),
                max_portion_g=_clean_optional_float(food.max_portion_g),
                portion_step_g=_clean_optional_float(food.portion_step_g),
                data_quality_score=int(food.data_quality_score or 0),
                is_verified=bool(food.is_verified),
            )
        )

    return foods


def _build_meal(
    *,
    template: MealTemplate,
    foods: list[DailyPlanGeneratorFood],
    excluded_terms: list[str],
    preferred_terms: list[str],
    meal_target: MealTarget,
    soft_avoid_ids: set[int],
) -> ProposedMealDTO:
    selection = _select_foods_for_meal(
        foods=foods,
        excluded_terms=excluded_terms,
        preferred_terms=preferred_terms,
        soft_avoid_ids=soft_avoid_ids,
        template=template,
    )
    foods_by_id = {food.food_id: food for food in foods}

    solver_foods = []
    for role_template in template.roles:
        food_id = selection.selected_roles.get(role_template.role)
        if food_id is None:
            if role_template.required:
                raise DailyPlanGeneratorError(f"dailyplan_generator_missing_required_{role_template.role}")
            continue

        solver_foods.append(
            _to_solver_food(
                food=foods_by_id[food_id],
                role_template=role_template,
            )
        )

    solver_result = solve_meal_portions(
        foods=solver_foods,
        target=meal_target.as_macro_target(),
    )
    proposed_foods = [
        ProposedFoodItemDTO(
            food_id=portion.food_id,
            quantity=portion.quantity_g,
        )
        for portion in solver_result.portions
    ]

    return ProposedMealDTO(
        name=f"{template.label} IA {template.index + 1}",
        foods=proposed_foods,
    )


def _select_foods_for_meal(
    *,
    foods: list[DailyPlanGeneratorFood],
    excluded_terms: list[str],
    preferred_terms: list[str],
    soft_avoid_ids: set[int],
    template: MealTemplate,
):
    selector_foods = [_to_selector_food(food) for food in foods]
    try:
        return select_meal_food_candidates(
            foods=selector_foods,
            excluded_terms=excluded_terms,
            preferred_terms=preferred_terms,
            soft_avoid_ids=soft_avoid_ids,
            is_snack=template.is_snack,
            include_vegetable=template.include_vegetable,
        )
    except CandidateSelectionError as exc:
        raise DailyPlanGeneratorError(str(exc)) from exc


def _to_selector_food(food: DailyPlanGeneratorFood) -> NutritionFoodCandidate:
    return NutritionFoodCandidate(
        food_id=food.food_id,
        name=food.name,
        protein=food.protein,
        carbs=food.carbs,
        fat=food.fat,
        kcal_per_100g=food.kcal_per_100g,
        food_group=food.food_group,
        food_subgroup=food.food_subgroup,
        data_quality_score=food.data_quality_score,
        is_verified=food.is_verified,
    )


def _to_solver_food(
    *,
    food: DailyPlanGeneratorFood,
    role_template: MealRoleTemplate,
) -> SolverFood:
    return SolverFood(
        food_id=food.food_id,
        name=food.name,
        role=role_template.role,
        protein_per_100g=food.protein,
        carbs_per_100g=food.carbs,
        fat_per_100g=food.fat,
        kcal_per_100g=food.kcal_per_100g,
        bounds=_solver_bounds_for_food(
            food=food,
            role_template=role_template,
        ),
        required=role_template.required,
    )


def _solver_bounds_for_food(
    *,
    food: DailyPlanGeneratorFood,
    role_template: MealRoleTemplate,
) -> PortionBounds:
    minimum = role_template.minimum_g
    maximum = role_template.maximum_g

    if food.min_portion_g is not None:
        minimum = max(minimum, food.min_portion_g)

    if food.max_portion_g is not None:
        maximum = min(maximum, food.max_portion_g)

    if maximum < minimum:
        maximum = minimum

    return PortionBounds(
        minimum_g=minimum,
        maximum_g=maximum,
        step_g=food.portion_step_g or role_template.step_g or 5,
    )


def _pick_food(
    *,
    foods: list[DailyPlanGeneratorFood],
    category: str,
    preferred_terms: list[str],
    excluded_terms: list[str],
    avoid_ids: set[int] | None = None,
    soft_avoid_ids: set[int] | None = None,
    required: bool = True,
) -> DailyPlanGeneratorFood | None:
    avoid_ids = avoid_ids or set()
    soft_avoid_ids = soft_avoid_ids or set()
    candidates = [
        food
        for food in foods
        if food.food_id not in avoid_ids
        and not _matches_any(_food_search_text(food), excluded_terms)
        and _category_score(food, category) > 0
    ]

    if not candidates and category == "vegetable":
        candidates = [
            food
            for food in foods
            if food.food_id not in avoid_ids
            and not _matches_any(_food_search_text(food), excluded_terms)
            and food.kcal_per_100g <= 80
            and food.fat <= 2
        ]

    if not candidates:
        if required:
            raise DailyPlanGeneratorError("dailyplan_generator_food_candidates_not_found")
        return None

    candidates.sort(
        key=lambda food: _food_score(
            food=food,
            category=category,
            preferred_terms=preferred_terms,
            soft_avoid_ids=soft_avoid_ids,
        ),
        reverse=True,
    )
    return candidates[0]


def _food_score(
    *,
    food: DailyPlanGeneratorFood,
    category: str,
    preferred_terms: list[str],
    soft_avoid_ids: set[int],
) -> float:
    score = _category_score(food, category) * 1000
    search_text = _food_search_text(food)

    if _matches_any(search_text, preferred_terms):
        score += 180

    if food.food_id in soft_avoid_ids:
        score -= 45

    if food.is_verified:
        score += 25

    score += min(food.data_quality_score, 100) / 5
    score += _macro_density_score(food, category)
    return score


def _category_score(food: DailyPlanGeneratorFood, category: str) -> float:
    search_text = _food_search_text(food)
    total_kcal = max(food.kcal_per_100g, 1)
    protein_alloc = food.protein * PROTEIN_KCAL_PER_GRAM / total_kcal
    carb_alloc = food.carbs * CARBS_KCAL_PER_GRAM / total_kcal
    fat_alloc = food.fat * FAT_KCAL_PER_GRAM / total_kcal

    if category == "protein":
        keyword_score = 1.0 if _matches_any(search_text, PROTEIN_KEYWORDS + PROTEIN_GROUP_KEYWORDS) else 0.0
        macro_score = protein_alloc if food.protein >= 6 else 0.0
        return max(keyword_score, macro_score)

    if category == "carb":
        keyword_score = 1.0 if _matches_any(search_text, CARB_KEYWORDS + CARB_GROUP_KEYWORDS) else 0.0
        macro_score = carb_alloc if food.carbs >= 8 else 0.0
        return max(keyword_score, macro_score)

    if category == "fat":
        keyword_score = 1.0 if _matches_any(search_text, FAT_KEYWORDS + FAT_GROUP_KEYWORDS) else 0.0
        macro_score = fat_alloc if food.fat >= 5 else 0.0
        return max(keyword_score, macro_score)

    if category == "vegetable":
        keyword_score = 1.0 if _matches_any(search_text, VEG_KEYWORDS + VEG_GROUP_KEYWORDS) else 0.0
        macro_score = 0.55 if food.kcal_per_100g <= 70 and food.fat <= 2 and food.protein <= 6 else 0.0
        return max(keyword_score, macro_score)

    return 0.0


def _macro_density_score(food: DailyPlanGeneratorFood, category: str) -> float:
    if category == "protein":
        return food.protein
    if category == "carb":
        return food.carbs / 2
    if category == "fat":
        return food.fat
    if category == "vegetable":
        return max(0, 80 - food.kcal_per_100g) / 4
    return 0.0


def _quantity_for_macro_target(
    *,
    food: DailyPlanGeneratorFood,
    macro: str,
    target_g: float,
    is_snack: bool,
) -> float:
    grams_per_100 = getattr(food, macro, 0.0)
    if grams_per_100 <= 0:
        return _portion_for_category(food=food, category=macro, is_snack=is_snack)

    quantity = (max(target_g, 0) / grams_per_100) * 100
    return _normalize_quantity(
        food=food,
        quantity=quantity,
        category=macro,
        is_snack=is_snack,
    )


def _quantity_for_energy_target(
    *,
    food: DailyPlanGeneratorFood,
    target_kcal: float,
    is_snack: bool,
) -> float:
    if food.kcal_per_100g <= 0:
        return _portion_for_category(food=food, category="carb", is_snack=is_snack)

    quantity = (max(target_kcal, 0) / food.kcal_per_100g) * 100
    return _normalize_quantity(
        food=food,
        quantity=quantity,
        category="carb",
        is_snack=is_snack,
    )


def _portion_for_category(
    *,
    food: DailyPlanGeneratorFood,
    category: str,
    is_snack: bool,
) -> float:
    if food.default_portion_g is not None:
        return _normalize_quantity(
            food=food,
            quantity=food.default_portion_g,
            category=category,
            is_snack=is_snack,
        )

    defaults = {
        "protein": 110 if is_snack else 170,
        "carb": 60 if is_snack else 140,
        "fat": 12 if is_snack else 20,
        "vegetable": 100,
    }
    return _normalize_quantity(
        food=food,
        quantity=defaults.get(category, 100),
        category=category,
        is_snack=is_snack,
    )


def _normalize_quantity(
    *,
    food: DailyPlanGeneratorFood,
    quantity: float,
    category: str,
    is_snack: bool,
) -> float:
    default_bounds = {
        "protein": (70 if is_snack else 90, 220 if is_snack else 280),
        "carb": (25 if is_snack else 45, 140 if is_snack else 240),
        "fat": (5, 25 if is_snack else 35),
        "vegetable": (50, 180),
    }
    minimum, maximum = default_bounds.get(category, (20, 300))

    if food.min_portion_g is not None:
        minimum = max(minimum, food.min_portion_g)

    if food.max_portion_g is not None:
        maximum = min(maximum, food.max_portion_g)

    if maximum < minimum:
        maximum = minimum

    step = food.portion_step_g or 5
    return _round_to_step(_clamp(quantity, minimum, maximum), step)


def _food_kcal(food: DailyPlanGeneratorFood | None, quantity: float) -> float:
    if food is None:
        return 0.0
    return food.kcal_per_100g * quantity / 100


def _normalize_meals_per_day(value: int | None) -> int:
    return normalize_template_meals_per_day(value)


def _build_dailyplan_name(brief: NutritionBrief) -> str:
    goal_label = brief.goal_label if brief.goal else "objetivo nutricional"
    return f"Plan IA - {goal_label}"


def _build_meal_note(
    *,
    template: MealTemplate,
    target_plan: DailyPlanTargetPlan,
) -> str:
    estimate_note = "targets estimados" if any(target_plan.estimated_targets.values()) else "targets definidos en brief"
    if template.is_snack:
        return f"{template.label} generado con template de snack y {estimate_note}; ajustar por preferencias antes de aplicar."

    return f"{template.label} generado con template {template.kind} y {estimate_note}; validar porciones antes de aplicar."


def _build_targets(target_plan: DailyPlanTargetPlan) -> dict:
    return target_plan.as_targets_dict()


def _build_validation_summary(
    *,
    brief: NutritionBrief,
    target_plan: DailyPlanTargetPlan,
    simulation: dict,
    solver_summary: dict | None = None,
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
            "strategy": "nutrition_engine_meal_templates_candidate_selector_solver",
            "source_intent": AI_NUTRITION_BRIEF_INTENT,
            "target_plan": target_plan.as_targets_dict(),
            "subject_context": _build_subject_context_snapshot(brief=brief, target_plan=target_plan),
            "meal_templates": [
                template.as_dict()
                for template in build_dailyplan_meal_templates(
                    _normalize_meals_per_day(brief.meals_per_day)
                )
            ],
            "notes": [
                "Generador heurístico inicial: estima targets si el brief no los trae completos.",
                "Estructura comidas con templates por tipo antes de seleccionar alimentos.",
                "Selecciona candidatos por rol nutricional, calidad, preferencias, exclusiones y repetición suave.",
                "Estima targets con Target Estimator formal y calcula porciones con solver v2 multi-start.",
                "La propuesta debe revisarse antes de aplicar el DailyPlan final.",
            ],
        },
        "target_comparison": _build_target_comparison(
            targets=_build_targets(target_plan),
            kpis=kpis,
        ),
        "engine_validation": _build_engine_validation_summary(
            target_plan=target_plan,
            kpis=kpis,
            brief=brief,
            simulation=simulation,
        ),
        "nutrition_solver": dict(solver_summary or {}),
        "brief": {
            "goal": brief.goal,
            "requested_entity": brief.requested_entity,
            "meals_per_day": brief.meals_per_day,
            "training_frequency": brief.training_frequency,
            "style_preferences": list(brief.style_preferences),
            "excluded_foods": list(brief.excluded_foods),
            "preferred_foods": list(brief.preferred_foods),
            "subject_source": brief.subject_source,
            "ppk_weight_source": brief.ppk_weight_source,
            "requires_library_ppk_warning": brief.requires_library_ppk_warning,
        },
    }


def _build_subject_context_snapshot(
    *,
    brief: NutritionBrief,
    target_plan: DailyPlanTargetPlan,
) -> dict:
    return {
        "source": brief.subject_source,
        "ppk_weight_source": brief.ppk_weight_source,
        "requires_library_ppk_warning": brief.requires_library_ppk_warning,
        "calculation_weight_kg": round(float(target_plan.weight_kg), 2),
        "calculation_height_cm": brief.height_cm,
        "calculation_age_years": brief.age_years,
        "calculation_sex": brief.sex,
        "calculation_activity_level": brief.activity_level,
        "calculation_training_frequency": brief.training_frequency,
    }


def _build_engine_validation_summary(
    *,
    target_plan: DailyPlanTargetPlan,
    kpis: dict,
    brief: NutritionBrief,
    simulation: dict,
) -> dict:
    target = MacroTarget(
        kcal=target_plan.total_kcal,
        protein=target_plan.protein,
        carbs=target_plan.carbs,
        fat=target_plan.fat,
    )
    actual = MacroTarget(
        kcal=float(kpis.get("total_kcal") or 0),
        protein=float(kpis.get("protein") or 0),
        carbs=float(kpis.get("carbs") or 0),
        fat=float(kpis.get("fat") or 0),
    )
    legacy_validation = compare_macro_targets(
        target=target,
        actual=actual,
    ).as_dict()
    strict_validation = validate_generated_dailyplan(
        target=target,
        actual=actual,
        expected_meals_count=_normalize_meals_per_day(brief.meals_per_day),
        actual_meals_count=_simulation_meal_count(simulation),
        excluded_terms=brief.excluded_foods,
        portions=_extract_simulation_portions(simulation),
    ).as_dict()

    return {
        **legacy_validation,
        "kind": "strict_dailyplan_nutrition_validation",
        "status": strict_validation["status"],
        "is_valid": strict_validation["is_valid"],
        "has_warnings": strict_validation["has_warnings"],
        "has_errors": strict_validation["has_errors"],
        "issues": strict_validation["issues"],
        "summary": strict_validation["summary"],
        "strict": strict_validation,
    }


def _simulation_meal_count(simulation: dict) -> int | None:
    dailyplan = simulation.get("dailyplan") or {}
    meals = dailyplan.get("meals")
    if isinstance(meals, list):
        return len(meals)
    return None


def _extract_simulation_portions(simulation: dict) -> list[PortionValidationInput]:
    dailyplan = simulation.get("dailyplan") or {}
    meals = dailyplan.get("meals") or []
    portions: list[PortionValidationInput] = []

    for meal in meals:
        meal_payload = meal.get("meal") or {}
        for food in meal_payload.get("foods") or []:
            portions.append(
                PortionValidationInput(
                    food_id=int(food.get("food_id") or 0),
                    food_name=str(food.get("food_name") or "Alimento"),
                    quantity_g=float(food.get("quantity") or 0),
                    role=_infer_role_from_simulated_food(food),
                )
            )

    return portions


def _infer_role_from_simulated_food(food: dict) -> str:
    quantity = float(food.get("quantity") or 0)
    total_kcal = float(food.get("total_kcal") or 0)
    kcal_per_100g = total_kcal / quantity * 100 if quantity > 0 else 0

    if kcal_per_100g <= 80 and float(food.get("fat") or 0) <= 3:
        return "vegetable"

    macro_kcal = {
        "protein": float(food.get("kcal_protein") or 0),
        "carb": float(food.get("kcal_carbs") or 0),
        "fat": float(food.get("kcal_fat") or 0),
    }

    role, value = max(macro_kcal.items(), key=lambda item: item[1])
    if value <= 0:
        return "unknown"
    return role


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
            "target": round(float(target), 2),
            "actual": round(float(actual), 2),
            "diff": round(diff, 2),
            "diff_percent": round((diff / float(target)) * 100, 2) if float(target) else None,
            "is_estimated_target": bool((targets.get("estimated_targets") or {}).get(target_key)),
        }

    return comparison


def _build_generated_proposal_title(brief: NutritionBrief) -> str:
    return f"DailyPlan IA - {brief.goal_label if brief.goal else 'Primer plan'}"


def _build_generated_proposal_summary(
    *,
    brief: NutritionBrief,
    target_plan: DailyPlanTargetPlan,
) -> str:
    pieces = [
        "Propuesta concreta generada desde NutritionBrief.",
        f"Objetivo: {brief.goal_label}.",
        f"Comidas: {_normalize_meals_per_day(brief.meals_per_day)}.",
        f"Targets usados: {round(target_plan.total_kcal)} kcal, {round(target_plan.protein)} g proteína, {round(target_plan.carbs)} g carbohidratos, {round(target_plan.fat)} g grasa.",
        f"Sujeto de cálculo: {brief.subject_source_label}.",
    ]

    if any(target_plan.estimated_targets.values()):
        pieces.append("Algunos targets fueron estimados provisionalmente por MyScoope.")

    if brief.style_preferences:
        pieces.append(f"Estilo: {', '.join(brief.style_preferences)}.")

    if brief.excluded_foods:
        pieces.append(f"Excluye: {', '.join(brief.excluded_foods)}.")

    if brief.requires_library_ppk_warning:
        pieces.append("Advertencia: el PPK de librería puede recalcularse con la ficha personal del usuario si esta propuesta externa se guarda.")

    pieces.append("Generador conectado al motor nutricional con Target Estimator formal y solver de porciones v2.")
    return " ".join(pieces)


def _normalize_terms(values: Iterable[str]) -> list[str]:
    return [
        _normalize_text(value)
        for value in values
        if _normalize_text(value)
    ]


def _normalize_text(value: str) -> str:
    text = " ".join(str(value or "").strip().lower().split())
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )


def _matches_any(text: str, terms: Iterable[str]) -> bool:
    normalized = _normalize_text(text)
    return any(term and _normalize_text(term) in normalized for term in terms)


def _food_search_text(food: DailyPlanGeneratorFood) -> str:
    return _normalize_text(" ".join((food.name, food.food_group, food.food_subgroup)))


def _is_snack_label(label: str) -> bool:
    normalized = _normalize_text(label)
    return normalized in {"snack", "media manana", "colacion"}


def _clean_optional_float(value) -> float | None:
    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    return number if number > 0 else None


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(float(value), maximum))


def _round_to_step(value: float, step: float) -> float:
    step = step or 5
    return float(round(float(value) / step) * step)
