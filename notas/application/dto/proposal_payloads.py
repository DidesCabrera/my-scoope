"""Public proposal payload contract, composed without cyclic dependencies."""

from typing import Any

from notas.application.dto.meal_plan_payloads import (
    CREATE_DAILYPLAN_INTENT,
    CREATE_MEAL_INTENT,
    DEFAULT_PROPOSED_FOOD_UNIT,
    MAX_PROPOSED_DAILYPLAN_MEALS,
    MIN_PROPOSED_DAILYPLAN_MEALS,
    MIN_PROPOSED_MEAL_FOODS,
    ProposedDailyPlanDTO,
    ProposedDailyPlanMealDTO,
    ProposedDailyPlanPayloadDTO,
    ProposedFoodItemDTO,
    ProposedMealDTO,
    ProposedMealPayloadDTO,
    parse_proposed_dailyplan_payload,
    parse_proposed_food_item_payload,
    parse_proposed_meal_payload,
)
from notas.application.dto.program_proposal import ProposedProgramPayload, parse_program_payload

CREATE_PROGRAM_INTENT = "create_program"
SUPPORTED_PROPOSAL_PAYLOAD_INTENTS = {CREATE_MEAL_INTENT, CREATE_DAILYPLAN_INTENT, CREATE_PROGRAM_INTENT}


def parse_proposal_payload(payload: dict[str, Any]) -> ProposedMealPayloadDTO | ProposedDailyPlanPayloadDTO | ProposedProgramPayload:
    if not isinstance(payload, dict):
        raise ValueError("proposal_payload_must_be_object")
    parser = {CREATE_MEAL_INTENT: parse_proposed_meal_payload,
              CREATE_DAILYPLAN_INTENT: parse_proposed_dailyplan_payload,
              CREATE_PROGRAM_INTENT: parse_program_payload}.get(payload.get("intent"))
    if parser is None:
        raise ValueError("unsupported_proposal_payload_intent")
    return parser(payload)
