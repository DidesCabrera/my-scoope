"""Small value normalizers for the conversational nutrition brief."""

from __future__ import annotations


def parse_float(value: object) -> float | None:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def clean_float(value: object, *, min_value: float, max_value: float) -> float | None:
    parsed = parse_float(value)
    if parsed is None or parsed < min_value or parsed > max_value:
        return None
    return round(parsed, 2)


def clean_macro_distribution(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    cleaned = {
        key: clean_float(value.get(key), min_value=0.01, max_value=99.99)
        for key in ("protein", "carbs", "fat")
    }
    if any(item is None for item in cleaned.values()):
        return {}
    return {key: float(item) for key, item in cleaned.items()}
