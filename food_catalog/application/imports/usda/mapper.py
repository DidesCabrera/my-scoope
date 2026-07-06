from decimal import Decimal, InvalidOperation

from food_catalog.application.imports.contracts import ImportedFoodDTO
from food_catalog.application.imports.sources import SOURCE_USDA


USDA_SOURCE_DATASET_DEFAULT = "food_data_central"

USDA_NUTRIENT_PROTEIN = "203"
USDA_NUTRIENT_FAT = "204"
USDA_NUTRIENT_CARBS = "205"
USDA_NUTRIENT_FIBER = "291"
USDA_NUTRIENT_SUGARS = "269"
USDA_NUTRIENT_SATURATED_FAT = "606"
USDA_NUTRIENT_SODIUM = "307"


def map_usda_food_to_imported_food_dto(
    payload: dict,
    *,
    source_version: str,
    source_dataset: str = USDA_SOURCE_DATASET_DEFAULT,
) -> ImportedFoodDTO:
    """
    Map a minimal USDA FoodData Central-like payload into ImportedFoodDTO.

    This mapper intentionally supports a small, controlled shape first.

    Expected payload shape:

    {
        "fdcId": 12345,
        "description": "Oats, raw",
        "foodCategory": {"description": "Cereal Grains and Pasta"},
        "foodNutrients": [
            {
                "nutrient": {
                    "number": "203",
                    "name": "Protein",
                    "unitName": "g"
                },
                "amount": 16.9
            }
        ]
    }

    Data safety:
    - This mapper does not write to the database.
    - It only converts external data into the internal import contract.
    - Validation and persistence remain responsibility of the existing pipeline.
    """

    nutrients = _extract_nutrients_by_number(payload)

    return ImportedFoodDTO(
        source=SOURCE_USDA,
        source_food_id=str(payload.get("fdcId", "")).strip(),
        source_dataset=source_dataset,
        source_version=source_version,
        name=str(payload.get("description", "")).strip(),
        canonical_name=str(payload.get("description", "")).strip(),
        protein=_get_nutrient_amount(nutrients, USDA_NUTRIENT_PROTEIN),
        carbs=_get_usda_required_macro_amount(nutrients, USDA_NUTRIENT_CARBS),
        fat=_get_nutrient_amount(nutrients, USDA_NUTRIENT_FAT),
        food_group=_extract_food_group(payload),
        food_subgroup="",
        fiber_g_per_100g=_get_optional_nutrient_amount(nutrients, USDA_NUTRIENT_FIBER),
        sugar_g_per_100g=_get_optional_nutrient_amount(nutrients, USDA_NUTRIENT_SUGARS),
        saturated_fat_g_per_100g=_get_optional_nutrient_amount(
            nutrients,
            USDA_NUTRIENT_SATURATED_FAT,
        ),
        sodium_mg_per_100g=_get_optional_nutrient_amount(nutrients, USDA_NUTRIENT_SODIUM),
        license_name="CC0",
        attribution="USDA FoodData Central",
        source_url="",
        raw_payload_hash="",
        normalized_payload_hash="",
    )


def _extract_nutrients_by_number(payload: dict) -> dict[str, Decimal]:
    nutrients_by_number = {}

    for item in payload.get("foodNutrients", []) or []:
        nutrient = item.get("nutrient", {}) or {}
        nutrient_number = str(nutrient.get("number", "")).strip()

        if not nutrient_number:
            continue

        amount = _to_decimal(item.get("amount"))

        nutrients_by_number[nutrient_number] = amount

    return nutrients_by_number


def _get_nutrient_amount(
    nutrients: dict[str, Decimal],
    nutrient_number: str,
) -> Decimal:
    return nutrients.get(nutrient_number, Decimal("0"))


def _get_usda_required_macro_amount(
    nutrients: dict[str, Decimal],
    nutrient_number: str,
) -> Decimal:
    """
    Return a required USDA macro amount normalized for app usage.

    Some USDA Foundation Foods can report negative carbohydrate values for
    animal-based foods due to analytical/calculation details. My Scoope should
    never expose negative macro grams to users, and for carbohydrates the
    operationally correct value is zero.

    Protein and fat remain handled by the generic getter so unexpected negative
    values still fail quality validation.
    """

    amount = _get_nutrient_amount(nutrients, nutrient_number)

    if nutrient_number == USDA_NUTRIENT_CARBS and amount < 0:
        return Decimal("0")

    return amount


def _get_optional_nutrient_amount(
    nutrients: dict[str, Decimal],
    nutrient_number: str,
) -> Decimal | None:
    if nutrient_number not in nutrients:
        return None

    return nutrients[nutrient_number]


def _extract_food_group(payload: dict) -> str:
    category = payload.get("foodCategory")

    if isinstance(category, dict):
        return str(category.get("description", "")).strip()

    if isinstance(category, str):
        return category.strip()

    return ""


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")