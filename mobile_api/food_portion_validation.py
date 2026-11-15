"""Validate the optional suggested portion on private food writes."""

from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.libraries import FoodCreateInput


def validate_food_portion_input(payload: FoodCreateInput) -> None:
    if (payload.household_amount is None) != (not payload.household_measure):
        raise MobileAPIError("food_household_portion_incomplete", "Completa la cantidad y la medida de la equivalencia.", 422)
    if payload.household_amount is not None and payload.default_portion is None:
        raise MobileAPIError("food_household_portion_incomplete", "Ingresa la porción sugerida antes de agregar una equivalencia.", 422)
    if payload.household_measure == "other" and not 1 <= len(payload.household_detail.strip()) <= 100:
        raise MobileAPIError("food_household_label_required", "Escribe una medida cotidiana de hasta 100 caracteres.", 422)


def validate_food_portion_update(payload: FoodCreateInput) -> bool:
    fields = {"default_portion", "household_amount", "household_measure", "household_detail"}
    update_portion = bool(fields & payload.model_fields_set)
    if update_portion and not fields <= payload.model_fields_set:
        raise MobileAPIError("food_household_portion_incomplete", "Envía todos los datos de la porción sugerida.", 422)
    if update_portion:
        validate_food_portion_input(payload)
    return update_portion
