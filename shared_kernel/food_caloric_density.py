"""Versioned, unified calorie-density rule for catalog and operational foods.

The six intervals were fitted in log space to 222 published catalog foods in
November 2026. Their boundaries are frozen for this version.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

CALORIC_DENSITY_VERSION = "caloric_density_log6_2026_11_v1"
CALORIC_DENSITY_BOUNDARIES = tuple(
    Decimal(value) for value in ("0.2558", "0.4865", "0.9477", "2.0540", "4.5314")
)
CALORIC_DENSITY_CHOICES = tuple((f"D{index}", f"D{index}") for index in range(1, 7))


def _nonnegative(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return number if number.is_finite() and number >= 0 else None


def calculate_caloric_density(
    declared_kcal_per_100: object,
    protein_per_100: object,
    carbs_per_100: object,
    fat_per_100: object,
    portion_unit: str,
) -> tuple[Decimal | None, str, str, bool]:
    """Return (kcal/unit, D1–D6, source, approximate-volume flag).

    The unit is g for solids and ml for liquids. A liquid's source nutrition may
    actually be per 100 g; interpreting it per 100 ml uses the explicit 1 g/ml
    approximation. Missing energy and unusable macros remain unclassified.
    """

    declared = _nonnegative(declared_kcal_per_100)
    if declared is not None:
        energy = declared
        source = "declared"
    else:
        macros = tuple(_nonnegative(value) for value in (protein_per_100, carbs_per_100, fat_per_100))
        if any(value is None for value in macros):
            return None, "", "", portion_unit == "ml"
        energy = macros[0] * 4 + macros[1] * 4 + macros[2] * 9
        if energy <= 0:
            return None, "", "", portion_unit == "ml"
        source = "macro_4_4_9"

    density = (energy / 100).quantize(Decimal("0.0001"))
    segment = next(
        (f"D{index}" for index, boundary in enumerate(CALORIC_DENSITY_BOUNDARIES, 1) if density < boundary),
        "D6",
    )
    return density, segment, source, portion_unit == "ml"
