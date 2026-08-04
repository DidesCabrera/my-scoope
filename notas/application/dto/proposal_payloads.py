from dataclasses import asdict, dataclass
from typing import Any

CREATE_MEAL_INTENT = "create_meal"
CREATE_DAILYPLAN_INTENT = "create_dailyplan"

DEFAULT_PROPOSED_FOOD_UNIT = "g"

MIN_PROPOSED_MEAL_FOODS = 1
MIN_PROPOSED_DAILYPLAN_MEALS = 1
MAX_PROPOSED_DAILYPLAN_MEALS = 10

SUPPORTED_PROPOSAL_PAYLOAD_INTENTS = {
    CREATE_MEAL_INTENT,
    CREATE_DAILYPLAN_INTENT,
}


@dataclass(frozen=True)
class ProposedFoodItemDTO:
    food_id: int
    quantity: float
    unit: str = "g"

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ProposedMealDTO:
    name: str
    foods: list[ProposedFoodItemDTO]

    def as_dict(self) -> dict:
        data = asdict(self)
        data["foods"] = [
            food.as_dict()
            for food in self.foods
        ]
        return data


@dataclass(frozen=True)
class ProposedDailyPlanMealDTO:
    hour: str | None
    note: str
    meal: ProposedMealDTO

    def as_dict(self) -> dict:
        data = asdict(self)
        data["meal"] = self.meal.as_dict()
        return data


@dataclass(frozen=True)
class ProposedDailyPlanDTO:
    name: str
    meals: list[ProposedDailyPlanMealDTO]

    def as_dict(self) -> dict:
        data = asdict(self)
        data["meals"] = [
            meal.as_dict()
            for meal in self.meals
        ]
        return data


@dataclass(frozen=True)
class ProposedMealPayloadDTO:
    intent: str
    meal: ProposedMealDTO

    def as_dict(self) -> dict:
        return {
            "intent": self.intent,
            "meal": self.meal.as_dict(),
        }


@dataclass(frozen=True)
class ProposedDailyPlanPayloadDTO:
    intent: str
    dailyplan: ProposedDailyPlanDTO

    def as_dict(self) -> dict:
        return {
            "intent": self.intent,
            "dailyplan": self.dailyplan.as_dict(),
        }


def _normalize_optional_hour(hour: Any) -> str | None:
    if hour is None:
        return None

    if not isinstance(hour, str):
        raise ValueError("proposed_dailyplan_meal_hour_must_be_string")

    normalized_hour = hour.strip()

    if not normalized_hour:
        return None

    parts = normalized_hour.split(":")

    if len(parts) != 2:
        raise ValueError("proposed_dailyplan_meal_hour_must_use_hh_mm_format")

    hour_part, minute_part = parts

    if not hour_part.isdigit() or not minute_part.isdigit():
        raise ValueError("proposed_dailyplan_meal_hour_must_use_hh_mm_format")

    hour_number = int(hour_part)
    minute_number = int(minute_part)

    if hour_number < 0 or hour_number > 23:
        raise ValueError("proposed_dailyplan_meal_hour_out_of_range")

    if minute_number < 0 or minute_number > 59:
        raise ValueError("proposed_dailyplan_meal_hour_out_of_range")

    return f"{hour_number:02d}:{minute_number:02d}"



def parse_proposed_food_item_payload(payload: dict[str, Any]) -> ProposedFoodItemDTO:
    if not isinstance(payload, dict):
        raise ValueError("proposed_food_item_payload_must_be_object")

    food_id = payload.get("food_id")
    quantity = payload.get("quantity")
    unit = payload.get("unit", DEFAULT_PROPOSED_FOOD_UNIT)

    if not isinstance(food_id, int):
        raise ValueError("proposed_food_item_food_id_required")

    if isinstance(quantity, bool) or not isinstance(quantity, int | float):
        raise ValueError("proposed_food_item_quantity_required")

    quantity = float(quantity)

    if quantity <= 0:
        raise ValueError("proposed_food_item_quantity_must_be_positive")

    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("proposed_food_item_unit_required")

    return ProposedFoodItemDTO(
        food_id=food_id,
        quantity=quantity,
        unit=unit.strip(),
    )


def parse_proposed_meal_payload(payload: dict[str, Any]) -> ProposedMealPayloadDTO:
    if not isinstance(payload, dict):
        raise ValueError("proposed_meal_payload_must_be_object")

    intent = payload.get("intent")

    if intent != CREATE_MEAL_INTENT:
        raise ValueError("invalid_proposed_meal_payload_intent")

    meal_payload = payload.get("meal")

    if not isinstance(meal_payload, dict):
        raise ValueError("proposed_meal_payload_meal_required")

    name = meal_payload.get("name")
    foods_payload = meal_payload.get("foods")

    if not isinstance(name, str) or not name.strip():
        raise ValueError("proposed_meal_name_required")

    if not isinstance(foods_payload, list):
        raise ValueError("proposed_meal_foods_required")

    if len(foods_payload) < MIN_PROPOSED_MEAL_FOODS:
        raise ValueError("proposed_meal_foods_must_not_be_empty")

    foods = [
        parse_proposed_food_item_payload(food_payload)
        for food_payload in foods_payload
    ]

    return ProposedMealPayloadDTO(
        intent=CREATE_MEAL_INTENT,
        meal=ProposedMealDTO(
            name=name.strip(),
            foods=foods,
        ),
    )


def parse_proposed_dailyplan_payload(
    payload: dict[str, Any],
) -> ProposedDailyPlanPayloadDTO:
    if not isinstance(payload, dict):
        raise ValueError("proposed_dailyplan_payload_must_be_object")

    intent = payload.get("intent")

    if intent != CREATE_DAILYPLAN_INTENT:
        raise ValueError("invalid_proposed_dailyplan_payload_intent")

    dailyplan_payload = payload.get("dailyplan")

    if not isinstance(dailyplan_payload, dict):
        raise ValueError("proposed_dailyplan_payload_dailyplan_required")

    name = dailyplan_payload.get("name")
    meals_payload = dailyplan_payload.get("meals")

    if not isinstance(name, str) or not name.strip():
        raise ValueError("proposed_dailyplan_name_required")

    if not isinstance(meals_payload, list):
        raise ValueError("proposed_dailyplan_meals_required")

    if len(meals_payload) < MIN_PROPOSED_DAILYPLAN_MEALS:
        raise ValueError("proposed_dailyplan_meals_must_not_be_empty")

    if len(meals_payload) > MAX_PROPOSED_DAILYPLAN_MEALS:
        raise ValueError("proposed_dailyplan_meals_exceeds_maximum")

    meals = [
        _parse_proposed_dailyplan_meal_payload(meal_payload)
        for meal_payload in meals_payload
    ]

    return ProposedDailyPlanPayloadDTO(
        intent=CREATE_DAILYPLAN_INTENT,
        dailyplan=ProposedDailyPlanDTO(
            name=name.strip(),
            meals=meals,
        ),
    )


def _parse_proposed_dailyplan_meal_payload(
    payload: dict[str, Any],
) -> ProposedDailyPlanMealDTO:
    if not isinstance(payload, dict):
        raise ValueError("proposed_dailyplan_meal_payload_must_be_object")

    hour = _normalize_optional_hour(payload.get("hour"))
    note = payload.get("note", "")
    meal_payload = payload.get("meal")

    if not isinstance(note, str):
        raise ValueError("proposed_dailyplan_meal_note_must_be_string")

    if not isinstance(meal_payload, dict):
        raise ValueError("proposed_dailyplan_meal_meal_required")

    meal_name = meal_payload.get("name")
    foods_payload = meal_payload.get("foods")

    if not isinstance(meal_name, str) or not meal_name.strip():
        raise ValueError("proposed_dailyplan_meal_name_required")

    if not isinstance(foods_payload, list):
        raise ValueError("proposed_dailyplan_meal_foods_required")

    if len(foods_payload) < MIN_PROPOSED_MEAL_FOODS:
        raise ValueError("proposed_dailyplan_meal_foods_must_not_be_empty")

    foods = [
        parse_proposed_food_item_payload(food_payload)
        for food_payload in foods_payload
    ]

    return ProposedDailyPlanMealDTO(
        hour=hour,
        note=note.strip(),
        meal=ProposedMealDTO(
            name=meal_name.strip(),
            foods=foods,
        ),
    )


def parse_proposal_payload(
    payload: dict[str, Any],
) -> ProposedMealPayloadDTO | ProposedDailyPlanPayloadDTO:
    if not isinstance(payload, dict):
        raise ValueError("proposal_payload_must_be_object")

    intent = payload.get("intent")

    if intent == CREATE_MEAL_INTENT:
        return parse_proposed_meal_payload(payload)

    if intent == CREATE_DAILYPLAN_INTENT:
        return parse_proposed_dailyplan_payload(payload)

    raise ValueError("unsupported_proposal_payload_intent")
