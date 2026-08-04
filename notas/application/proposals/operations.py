from dataclasses import asdict, dataclass

OPERATION_UPDATE_MEAL_FOOD_QUANTITY = "update_meal_food_quantity"


SUPPORTED_PROPOSAL_OPERATION_TYPES = {
    OPERATION_UPDATE_MEAL_FOOD_QUANTITY,
}


@dataclass(frozen=True)
class UpdateMealFoodQuantityOperation:
    type: str
    mealfood_id: int
    from_quantity: float
    to_quantity: float

    def as_dict(self) -> dict:
        return asdict(self)


def _require_keys(
    *,
    operation: dict,
    required_keys: set[str],
) -> None:
    missing_keys = required_keys - set(operation.keys())

    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ValueError(f"proposal_operation_missing_keys:{missing}")


def _parse_float(value, error_code: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(error_code)


def _parse_int(value, error_code: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(error_code)


def parse_update_meal_food_quantity_operation(
    operation: dict,
) -> UpdateMealFoodQuantityOperation:
    _require_keys(
        operation=operation,
        required_keys={
            "type",
            "mealfood_id",
            "from_quantity",
            "to_quantity",
        },
    )

    mealfood_id = _parse_int(
        operation["mealfood_id"],
        "proposal_operation_invalid_mealfood_id",
    )
    from_quantity = _parse_float(
        operation["from_quantity"],
        "proposal_operation_invalid_from_quantity",
    )
    to_quantity = _parse_float(
        operation["to_quantity"],
        "proposal_operation_invalid_to_quantity",
    )

    if mealfood_id <= 0:
        raise ValueError("proposal_operation_invalid_mealfood_id")

    if from_quantity < 0:
        raise ValueError("proposal_operation_invalid_from_quantity")

    if to_quantity <= 0:
        raise ValueError("proposal_operation_invalid_to_quantity")

    return UpdateMealFoodQuantityOperation(
        type=OPERATION_UPDATE_MEAL_FOOD_QUANTITY,
        mealfood_id=mealfood_id,
        from_quantity=from_quantity,
        to_quantity=to_quantity,
    )


def parse_proposal_operation(
    operation: dict,
):
    if not isinstance(operation, dict):
        raise ValueError("proposal_operation_must_be_object")

    operation_type = operation.get("type")

    if operation_type not in SUPPORTED_PROPOSAL_OPERATION_TYPES:
        raise ValueError("unsupported_proposal_operation_type")

    if operation_type == OPERATION_UPDATE_MEAL_FOOD_QUANTITY:
        return parse_update_meal_food_quantity_operation(operation)

    raise ValueError("unsupported_proposal_operation_type")


def parse_proposal_operations(
    proposed_payload: dict,
) -> list[UpdateMealFoodQuantityOperation]:
    if not isinstance(proposed_payload, dict):
        raise ValueError("proposal_payload_must_be_object")

    suggested_changes = proposed_payload.get("suggested_changes", [])

    if not isinstance(suggested_changes, list):
        raise ValueError("proposal_suggested_changes_must_be_list")

    return [
        parse_proposal_operation(operation)
        for operation in suggested_changes
    ]