from dataclasses import asdict, dataclass
from typing import Any

from django.shortcuts import get_object_or_404

from notas.application.dto.program_proposal import ProposedProgramPayload
from notas.application.dto.proposal_payloads import (
    ProposedDailyPlanPayloadDTO,
    ProposedFoodItemDTO,
    ProposedMealDTO,
    ProposedMealPayloadDTO,
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


@dataclass(frozen=True)
class SimulatedFoodItemDTO:
    food_id: int
    food_name: str
    quantity: float
    unit: str
    protein: float
    carbs: float
    fat: float
    kcal_protein: float
    kcal_carbs: float
    kcal_fat: float
    total_kcal: float

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SimulatedNutritionKPIDTO:
    total_kcal: float
    protein: float
    carbs: float
    fat: float
    kcal_protein: float
    kcal_carbs: float
    kcal_fat: float
    alloc_protein: float
    alloc_carbs: float
    alloc_fat: float
    ppk: float | None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SimulatedMealDTO:
    name: str
    foods: list[SimulatedFoodItemDTO]
    kpis: SimulatedNutritionKPIDTO

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "foods": [
                food.as_dict()
                for food in self.foods
            ],
            "kpis": self.kpis.as_dict(),
        }


@dataclass(frozen=True)
class SimulatedDailyPlanMealDTO:
    hour: str | None
    note: str
    meal: SimulatedMealDTO

    def as_dict(self) -> dict:
        return {
            "hour": self.hour,
            "note": self.note,
            "meal": self.meal.as_dict(),
        }


@dataclass(frozen=True)
class SimulatedDailyPlanDTO:
    name: str
    meals: list[SimulatedDailyPlanMealDTO]
    kpis: SimulatedNutritionKPIDTO

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "meals": [
                meal.as_dict()
                for meal in self.meals
            ],
            "kpis": self.kpis.as_dict(),
        }


@dataclass(frozen=True)
class ProposalPayloadSimulationDTO:
    intent: str
    meal: SimulatedMealDTO | None = None
    dailyplan: SimulatedDailyPlanDTO | None = None
    program: dict | None = None

    def as_dict(self) -> dict:
        return {
            "intent": self.intent,
            "meal": self.meal.as_dict() if self.meal else None,
            "dailyplan": self.dailyplan.as_dict() if self.dailyplan else None,
            "program": self.program,
        }


def simulate_proposal_payload(
    user,
    payload: dict[str, Any],
) -> ProposalPayloadSimulationDTO:
    """
    Simula nutricionalmente un proposed_payload.

    Esta query es read-only:
    - no crea Meal;
    - no crea DailyPlan;
    - no crea MealFood;
    - no modifica NutritionProposal.

    Solo valida el payload, lee foods visibles para el usuario y calcula KPIs.
    """
    parsed_payload = validate_proposal_payload_or_raise(payload)

    if isinstance(parsed_payload, ProposedProgramPayload):
        food_ids = {item.food_id for day in parsed_payload.days for entry in day.dailyplan.meals
                    for item in entry.meal.foods}
        # Resolve visibility once for the entire program, not once per portion
        # across 56 days. This snapshot is local to this call/user (no cache leak).
        foods = get_readable_food_queryset(user).in_bulk(food_ids)
        if food_ids.difference(foods):
            get_object_or_404(get_readable_food_queryset(user).none())
        return ProposalPayloadSimulationDTO(intent=parsed_payload.intent, program={
            "name": parsed_payload.name, "duration_weeks": parsed_payload.duration_weeks,
            "days": [{"week_number": day.week_number, "day_number": day.day_number, "dailyplan": simulate_proposed_dailyplan(user, day.dailyplan, _foods=foods).as_dict()} for day in parsed_payload.days],
        })

    if isinstance(parsed_payload, ProposedMealPayloadDTO):
        return ProposalPayloadSimulationDTO(
            intent=parsed_payload.intent,
            meal=simulate_proposed_meal(
                user=user,
                meal=parsed_payload.meal,
            ),
        )

    if isinstance(parsed_payload, ProposedDailyPlanPayloadDTO):
        return ProposalPayloadSimulationDTO(
            intent=parsed_payload.intent,
            dailyplan=simulate_proposed_dailyplan(
                user=user,
                dailyplan=parsed_payload.dailyplan,
            ),
        )

    raise ValueError("unsupported_proposal_payload_intent")


def simulate_proposed_meal(
    user,
    meal: ProposedMealDTO,
    *, _foods=None,
) -> SimulatedMealDTO:
    simulated_foods = [
        _simulate_food_item(
            user=user,
            food_item=food_item,
            _foods=_foods,
        )
        for food_item in meal.foods
    ]

    return SimulatedMealDTO(
        name=meal.name,
        foods=simulated_foods,
        kpis=_build_kpis_from_simulated_foods(
            user=user,
            foods=simulated_foods,
        ),
    )


def simulate_proposed_dailyplan(
    user,
    dailyplan,
    *, _foods=None,
) -> SimulatedDailyPlanDTO:
    simulated_meals = [
        SimulatedDailyPlanMealDTO(
            hour=dailyplan_meal.hour,
            note=dailyplan_meal.note,
            meal=simulate_proposed_meal(
                user=user,
                meal=dailyplan_meal.meal,
                _foods=_foods,
            ),
        )
        for dailyplan_meal in dailyplan.meals
    ]

    return SimulatedDailyPlanDTO(
        name=dailyplan.name,
        meals=simulated_meals,
        kpis=_build_kpis_from_simulated_meals(
            user=user,
            meals=[
                dailyplan_meal.meal
                for dailyplan_meal in simulated_meals
            ],
        ),
    )


def _simulate_food_item(
    user,
    food_item: ProposedFoodItemDTO,
    *, _foods=None,
) -> SimulatedFoodItemDTO:
    food = _foods[food_item.food_id] if _foods is not None else get_object_or_404(
        get_readable_food_queryset(user),
        pk=food_item.food_id,
    )

    factor = food_item.quantity / 100.0

    protein = float(food.protein) * factor
    carbs = float(food.carbs) * factor
    fat = float(food.fat) * factor

    kcal_protein = protein * PROTEIN_KCAL_PER_GRAM
    kcal_carbs = carbs * CARBS_KCAL_PER_GRAM
    kcal_fat = fat * FAT_KCAL_PER_GRAM
    total_kcal = kcal_protein + kcal_carbs + kcal_fat

    return SimulatedFoodItemDTO(
        food_id=food.id,
        food_name=food.name,
        quantity=food_item.quantity,
        unit=food_item.unit,
        protein=protein,
        carbs=carbs,
        fat=fat,
        kcal_protein=kcal_protein,
        kcal_carbs=kcal_carbs,
        kcal_fat=kcal_fat,
        total_kcal=total_kcal,
    )


def _build_kpis_from_simulated_foods(
    user,
    foods: list[SimulatedFoodItemDTO],
) -> SimulatedNutritionKPIDTO:
    protein = sum(food.protein for food in foods)
    carbs = sum(food.carbs for food in foods)
    fat = sum(food.fat for food in foods)

    kcal_protein = sum(food.kcal_protein for food in foods)
    kcal_carbs = sum(food.kcal_carbs for food in foods)
    kcal_fat = sum(food.kcal_fat for food in foods)

    return _build_kpis_from_values(
        user=user,
        protein=protein,
        carbs=carbs,
        fat=fat,
        kcal_protein=kcal_protein,
        kcal_carbs=kcal_carbs,
        kcal_fat=kcal_fat,
    )


def _build_kpis_from_simulated_meals(
    user,
    meals: list[SimulatedMealDTO],
) -> SimulatedNutritionKPIDTO:
    protein = sum(meal.kpis.protein for meal in meals)
    carbs = sum(meal.kpis.carbs for meal in meals)
    fat = sum(meal.kpis.fat for meal in meals)

    kcal_protein = sum(meal.kpis.kcal_protein for meal in meals)
    kcal_carbs = sum(meal.kpis.kcal_carbs for meal in meals)
    kcal_fat = sum(meal.kpis.kcal_fat for meal in meals)

    return _build_kpis_from_values(
        user=user,
        protein=protein,
        carbs=carbs,
        fat=fat,
        kcal_protein=kcal_protein,
        kcal_carbs=kcal_carbs,
        kcal_fat=kcal_fat,
    )


def _build_kpis_from_values(
    user,
    protein: float,
    carbs: float,
    fat: float,
    kcal_protein: float,
    kcal_carbs: float,
    kcal_fat: float,
) -> SimulatedNutritionKPIDTO:
    total_kcal = kcal_protein + kcal_carbs + kcal_fat

    if total_kcal > 0:
        alloc_protein = kcal_protein / total_kcal * 100
        alloc_carbs = kcal_carbs / total_kcal * 100
        alloc_fat = kcal_fat / total_kcal * 100
    else:
        alloc_protein = 0.0
        alloc_carbs = 0.0
        alloc_fat = 0.0

    weight = get_current_weight(user)
    ppk = protein / weight if weight and protein else None

    return SimulatedNutritionKPIDTO(
        total_kcal=total_kcal,
        protein=protein,
        carbs=carbs,
        fat=fat,
        kcal_protein=kcal_protein,
        kcal_carbs=kcal_carbs,
        kcal_fat=kcal_fat,
        alloc_protein=alloc_protein,
        alloc_carbs=alloc_carbs,
        alloc_fat=alloc_fat,
        ppk=ppk,
    )
