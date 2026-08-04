from dataclasses import dataclass
from decimal import Decimal

from food_catalog.application.imports.contracts import ImportedFoodDTO

MAX_MACRO_G_PER_100G = Decimal("100")
MAX_TOTAL_MACROS_G_PER_100G = Decimal("120")
MAX_SODIUM_MG_PER_100G = Decimal("100000")


@dataclass(frozen=True)
class ImportedFoodQualityResult:
    is_valid: bool
    reason: str = ""
    score: int = 0


def evaluate_imported_food_quality(dto: ImportedFoodDTO) -> ImportedFoodQualityResult:
    """
    Evaluate whether an imported food is safe enough to enter the global catalog.

    This is a defensive validation layer, not a final scientific validation
    system. Its purpose is to prevent obviously invalid external data from
    entering My Scoope.
    """

    missing_reason = _missing_required_reason(dto)
    if missing_reason:
        return ImportedFoodQualityResult(
            is_valid=False,
            reason=missing_reason,
            score=0,
        )

    invalid_macro_reason = _invalid_macro_reason(dto)
    if invalid_macro_reason:
        return ImportedFoodQualityResult(
            is_valid=False,
            reason=invalid_macro_reason,
            score=0,
        )

    invalid_extended_reason = _invalid_extended_nutrients_reason(dto)
    if invalid_extended_reason:
        return ImportedFoodQualityResult(
            is_valid=False,
            reason=invalid_extended_reason,
            score=0,
        )

    return ImportedFoodQualityResult(
        is_valid=True,
        reason="valid",
        score=_calculate_quality_score(dto),
    )


def _missing_required_reason(dto: ImportedFoodDTO) -> str:
    if not dto.source:
        return "missing_source"

    if not dto.source_food_id:
        return "missing_source_food_id"

    if not dto.name:
        return "missing_name"

    if not dto.canonical_name:
        return "missing_canonical_name"

    if dto.protein is None:
        return "missing_protein"

    if dto.carbs is None:
        return "missing_carbs"

    if dto.fat is None:
        return "missing_fat"

    return ""


def _invalid_macro_reason(dto: ImportedFoodDTO) -> str:
    if dto.protein < 0:
        return "invalid_negative_protein"

    if dto.carbs < 0:
        return "invalid_negative_carbs"

    if dto.fat < 0:
        return "invalid_negative_fat"

    if dto.protein > MAX_MACRO_G_PER_100G:
        return "invalid_protein_over_100g"

    if dto.carbs > MAX_MACRO_G_PER_100G:
        return "invalid_carbs_over_100g"

    if dto.fat > MAX_MACRO_G_PER_100G:
        return "invalid_fat_over_100g"

    total_macros = dto.protein + dto.carbs + dto.fat

    if total_macros > MAX_TOTAL_MACROS_G_PER_100G:
        return "invalid_total_macros_over_limit"

    return ""


def _invalid_extended_nutrients_reason(dto: ImportedFoodDTO) -> str:
    optional_gram_fields = {
        "fiber_g_per_100g": dto.fiber_g_per_100g,
        "sugar_g_per_100g": dto.sugar_g_per_100g,
        "saturated_fat_g_per_100g": dto.saturated_fat_g_per_100g,
    }

    for field_name, value in optional_gram_fields.items():
        if value is None:
            continue

        if value < 0:
            return f"invalid_negative_{field_name}"

        if value > MAX_MACRO_G_PER_100G:
            return f"invalid_{field_name}_over_100g"

    if dto.sodium_mg_per_100g is not None:
        if dto.sodium_mg_per_100g < 0:
            return "invalid_negative_sodium_mg_per_100g"

        if dto.sodium_mg_per_100g > MAX_SODIUM_MG_PER_100G:
            return "invalid_sodium_mg_per_100g_over_limit"

    return ""


def _calculate_quality_score(dto: ImportedFoodDTO) -> int:
    score = 60

    if dto.source_dataset:
        score += 5

    if dto.source_version:
        score += 5

    if dto.food_group:
        score += 5

    if dto.food_subgroup:
        score += 5

    if dto.fiber_g_per_100g is not None:
        score += 5

    if dto.sugar_g_per_100g is not None:
        score += 5

    if dto.saturated_fat_g_per_100g is not None:
        score += 5

    if dto.sodium_mg_per_100g is not None:
        score += 5

    return min(score, 100)