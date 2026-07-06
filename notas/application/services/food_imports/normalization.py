"""Compatibility wrapper for Food Catalog import normalization helpers."""

from food_catalog.application.imports.normalization import (
    normalize_food_name,
    normalize_imported_food,
)

__all__ = [
    "normalize_food_name",
    "normalize_imported_food",
]
