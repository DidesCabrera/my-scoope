"""Compatibility bridge for extracted nutrition validators.

Patch S7 moves validation dataclasses and functions to
``nutrition_solver.application.validators``. This module intentionally keeps the
legacy import path available for current ``notas`` services, tests and proposal
flows.
"""

from nutrition_solver.application.validators import (
    DEFAULT_ERROR_TOLERANCE_PERCENT,
    DEFAULT_REASONABLE_MAX_PORTION_G_BY_ROLE,
    DEFAULT_WARNING_TOLERANCE_PERCENT,
    METRIC_LABELS,
    STATUS_ERROR,
    STATUS_OK,
    STATUS_ORDER,
    STATUS_WARNING,
    NutritionValidationIssue,
    NutritionValidationResult,
    PortionValidationInput,
    StrictNutritionValidationConfig,
    StrictNutritionValidationResult,
    compare_macro_targets,
    validate_generated_dailyplan,
)

__all__ = [
    "DEFAULT_ERROR_TOLERANCE_PERCENT",
    "DEFAULT_REASONABLE_MAX_PORTION_G_BY_ROLE",
    "DEFAULT_WARNING_TOLERANCE_PERCENT",
    "METRIC_LABELS",
    "STATUS_ERROR",
    "STATUS_OK",
    "STATUS_ORDER",
    "STATUS_WARNING",
    "NutritionValidationIssue",
    "NutritionValidationResult",
    "PortionValidationInput",
    "StrictNutritionValidationConfig",
    "StrictNutritionValidationResult",
    "compare_macro_targets",
    "validate_generated_dailyplan",
]
