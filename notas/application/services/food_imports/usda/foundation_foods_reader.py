"""Compatibility wrapper for Food Catalog USDA Foundation Foods reader."""

from food_catalog.application.imports.usda.foundation_foods_reader import (
    FOUNDATION_FOODS_ROOT_KEYS,
    FoundationFoodsReaderError,
    extract_foundation_food_payloads,
    read_foundation_food_payloads_from_json,
)

__all__ = [
    "FOUNDATION_FOODS_ROOT_KEYS",
    "FoundationFoodsReaderError",
    "extract_foundation_food_payloads",
    "read_foundation_food_payloads_from_json",
]
