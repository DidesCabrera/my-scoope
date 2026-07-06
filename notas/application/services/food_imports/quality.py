"""Compatibility wrapper for Food Catalog import quality checks."""

from food_catalog.application.imports.quality import (
    ImportedFoodQualityResult,
    evaluate_imported_food_quality,
)

__all__ = [
    "ImportedFoodQualityResult",
    "evaluate_imported_food_quality",
]
