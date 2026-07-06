import json
from pathlib import Path
from typing import Any


class FoundationFoodsReaderError(ValueError):
    """Raised when a Foundation Foods JSON file cannot be read safely."""


FOUNDATION_FOODS_ROOT_KEYS = (
    "FoundationFoods",
    "foundationFoods",
    "foundation_foods",
    "foods",
    "FoodData",
    "foodData",
)


def read_foundation_food_payloads_from_json(path: str | Path) -> list[Any]:
    """
    Read USDA Foundation Foods payloads from a local JSON file.

    Supported root shapes:
    - a direct list
    - an object containing the food list under a known dataset root key

    Important:
    This reader intentionally does not enforce that every list item is a dict.
    Real USDA files may contain rows or entries that are not directly mappable
    by our importer. Those rows should be counted later by dry-run/import logic
    as mapping failures instead of aborting file reading entirely.

    This reader does not map, validate nutrients, or write to the database.
    """

    json_path = Path(path)

    try:
        with json_path.open("r", encoding="utf-8") as file:
            raw_payload = json.load(file)
    except json.JSONDecodeError as exc:
        raise FoundationFoodsReaderError(f"Invalid JSON file: {exc}") from exc
    except OSError as exc:
        raise FoundationFoodsReaderError(f"Could not read JSON file: {exc}") from exc

    return extract_foundation_food_payloads(raw_payload)


def extract_foundation_food_payloads(raw_payload: Any) -> list[Any]:
    """
    Extract Foundation Foods records from a decoded JSON payload.

    The reader is responsible for root-shape handling only.
    Row-level validation belongs to the dry-run/import pipeline.
    """

    if isinstance(raw_payload, list):
        return raw_payload

    if isinstance(raw_payload, dict):
        for root_key in FOUNDATION_FOODS_ROOT_KEYS:
            candidate = raw_payload.get(root_key)

            if candidate is not None:
                return _ensure_list(candidate, root_key=root_key)

        available_keys = ", ".join(sorted(str(key) for key in raw_payload.keys()))
        raise FoundationFoodsReaderError(
            "JSON root object does not contain a supported Foundation Foods list. "
            f"Supported keys: {', '.join(FOUNDATION_FOODS_ROOT_KEYS)}. "
            f"Available keys: {available_keys or '(none)'}"
        )

    raise FoundationFoodsReaderError(
        "JSON root must be either a list of USDA food payloads or an object "
        "containing a supported Foundation Foods list."
    )


def _ensure_list(
    candidate: Any,
    *,
    root_key: str,
) -> list[Any]:
    if not isinstance(candidate, list):
        raise FoundationFoodsReaderError(
            f"JSON root key '{root_key}' must contain a list of food payloads."
        )

    return candidate