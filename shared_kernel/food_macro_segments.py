"""Versioned calorie-composition segments shared by catalog and operational foods.

The seven centroids were fitted to the 157-food staging evaluation snapshot
``evaluation/foods_staging_2026-11-solver-v1.json`` captured on 2026-11-11.
Keep this v1 rule immutable; introduce a new version for any refit.
"""

from __future__ import annotations

import math
from collections.abc import Iterable


MACRO_SEGMENT_VERSION = "macro_kcal_7centers_2026_11_v1"
MACRO_SEGMENT_CENTERS = (
    ("A", (0.081319701022, 0.877903911913, 0.040776387065)),
    ("B", (0.236337030717, 0.687410176767, 0.076252792516)),
    ("C", (0.374412466268, 0.482432096025, 0.143155437706)),
    ("D", (0.823938137306, 0.076842441369, 0.099219421325)),
    ("E", (0.438221533101, 0.064618173610, 0.497160293289)),
    ("F", (0.211436909853, 0.116775993034, 0.671787097113)),
    ("G", (0.029459513585, 0.033777767423, 0.936762718992)),
)
MACRO_SEGMENT_CHOICES = tuple((label, label) for label, _ in MACRO_SEGMENT_CENTERS)


def _valid_macros(values: Iterable[object]) -> tuple[float, float, float] | None:
    try:
        protein, carbs, fat = (float(value) for value in values)
    except (TypeError, ValueError, OverflowError):
        return None
    if any(not math.isfinite(value) or value < 0 for value in (protein, carbs, fat)):
        return None
    return protein, carbs, fat


def classify_food_macro_segment(protein: object, carbs: object, fat: object) -> str:
    """Return A–G from normalized 4/4/9 macro kcal, or blank if unavailable.

    Equal squared Euclidean distances use alphabetical order as the tie-breaker.
    The inputs may be per 100 g, per 100 ml, or per serving; uniform scaling does
    not affect their energy shares. Label/source total kcal is intentionally not
    used because it can include energy outside these three reported macros.
    """

    macros = _valid_macros((protein, carbs, fat))
    if macros is None:
        return ""
    kcal = (macros[0] * 4, macros[1] * 4, macros[2] * 9)
    total = sum(kcal)
    if total <= 0 or not math.isfinite(total):
        return ""
    shares = tuple(value / total for value in kcal)
    return min(
        MACRO_SEGMENT_CENTERS,
        key=lambda item: sum((share - center) ** 2 for share, center in zip(shares, item[1])),
    )[0]
