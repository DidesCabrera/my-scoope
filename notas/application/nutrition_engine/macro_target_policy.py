"""Coherent daily protein-per-kg and macro target resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

PROTEIN_KCAL_PER_GRAM = 4.0
CARBS_KCAL_PER_GRAM = 4.0
FAT_KCAL_PER_GRAM = 9.0

MIN_SUPPORTED_PROTEIN_PER_KG = 1.0
MAX_SUPPORTED_PROTEIN_PER_KG = 2.5
MIN_PREFERRED_PROTEIN_PER_KG = 1.6
MAX_PREFERRED_PROTEIN_PER_KG = 2.2
MIN_SUPPORTED_FAT_ENERGY_PERCENT = 15.0
MAX_SUPPORTED_FAT_ENERGY_PERCENT = 35.0
DEFAULT_FAT_ENERGY_PERCENT = 25.0
ENERGY_COHERENCE_TOLERANCE = 0.05
MACRO_DISTRIBUTION_EQUIVALENCE_TOLERANCE = 0.5


@dataclass(frozen=True)
class MacroTargetResolution:
    protein: float
    carbs: float
    fat: float
    protein_per_kg: float
    distribution: dict[str, float]
    source: str
    notes: tuple[str, ...]


def resolve_daily_macro_targets(
    *,
    total_kcal: float,
    weight_kg: float,
    default_protein_per_kg: float,
    protein_target: float | None = None,
    carb_target: float | None = None,
    fat_target: float | None = None,
    protein_per_kg_target: float | None = None,
    macro_distribution: Mapping[str, object] | None = None,
    minimum_fat_g: float = 40.0,
    maximum_fat_g: float = 110.0,
) -> MacroTargetResolution:
    """Resolve one coherent daily target without silently overriding user inputs."""

    energy = _positive_float(total_kcal, "nutrition_target_kcal_must_be_positive")
    weight = _positive_float(weight_kg, "nutrition_target_weight_must_be_positive")
    distribution = normalize_macro_distribution(macro_distribution)
    explicit_grams = any(value is not None for value in (protein_target, carb_target, fat_target))
    requested_ppk = (
        _validated_ppk(protein_per_kg_target)
        if protein_per_kg_target is not None
        else _validated_ppk(default_protein_per_kg)
    )

    if distribution:
        protein = energy * distribution["protein"] / 100 / PROTEIN_KCAL_PER_GRAM
        carbs = energy * distribution["carbs"] / 100 / CARBS_KCAL_PER_GRAM
        fat = energy * distribution["fat"] / 100 / FAT_KCAL_PER_GRAM
        if explicit_grams:
            _validate_explicit_grams_match_distribution(
                total_kcal=energy,
                distribution=distribution,
                protein_target=protein_target,
                carb_target=carb_target,
                fat_target=fat_target,
            )
        derived_ppk = protein / weight
        _validate_derived_ppk(derived_ppk)
        if protein_per_kg_target is not None and not _close_protein_targets(
            protein,
            weight * requested_ppk,
        ):
            raise ValueError("nutrition_target_ppk_distribution_conflict")
        notes = ["Distribución energética explícita convertida a gramos por el backend."]
        if explicit_grams:
            notes.append(
                "Los gramos explícitos equivalentes se normalizaron usando la "
                "distribución solicitada como fuente de verdad."
            )
        notes.append(_ppk_range_note(derived_ppk))
        return MacroTargetResolution(
            protein=protein,
            carbs=carbs,
            fat=fat,
            protein_per_kg=derived_ppk,
            distribution=distribution,
            source="explicit_macro_distribution",
            notes=tuple(notes),
        )

    inferred_protein = _round_to_step(weight * requested_ppk, 5.0)
    protein = float(protein_target) if protein_target is not None else inferred_protein
    if protein_per_kg_target is not None and protein_target is not None and not _close_protein_targets(
        protein,
        inferred_protein,
    ):
        raise ValueError("nutrition_target_protein_ppk_conflict")

    remaining_after_protein = energy - protein * PROTEIN_KCAL_PER_GRAM
    if remaining_after_protein <= 0:
        raise ValueError("nutrition_target_protein_exceeds_energy")

    if fat_target is not None:
        fat = float(fat_target)
    elif carb_target is not None:
        fat = max(
            0.0,
            (remaining_after_protein - float(carb_target) * CARBS_KCAL_PER_GRAM)
            / FAT_KCAL_PER_GRAM,
        )
    else:
        fat = _round_to_step(
            _clamp(
                energy * DEFAULT_FAT_ENERGY_PERCENT / 100 / FAT_KCAL_PER_GRAM,
                minimum_fat_g,
                maximum_fat_g,
            ),
            5.0,
        )

    carbs = (
        float(carb_target)
        if carb_target is not None
        else _round_to_step(
            max(
                0.0,
                (energy - protein * PROTEIN_KCAL_PER_GRAM - fat * FAT_KCAL_PER_GRAM)
                / CARBS_KCAL_PER_GRAM,
            ),
            5.0,
        )
    )
    _validate_resolved_targets(energy=energy, protein=protein, carbs=carbs, fat=fat)
    actual_distribution = macro_distribution_from_grams(
        total_kcal=energy,
        protein=protein,
        carbs=carbs,
        fat=fat,
    )
    return MacroTargetResolution(
        protein=protein,
        carbs=carbs,
        fat=fat,
        protein_per_kg=protein / weight,
        distribution=actual_distribution,
        source=(
            "explicit_macro_grams"
            if explicit_grams
            else "protein_per_kg_fat_bound_carbohydrate_remainder"
        ),
        notes=(
            "Proteína resuelta por gramos/kg; grasa acotada; carbohidratos como energía restante.",
            _ppk_range_note(protein / weight),
        ),
    )


def normalize_macro_distribution(
    value: Mapping[str, object] | None,
) -> dict[str, float] | None:
    if not value:
        return None
    aliases = {
        "protein": ("protein", "protein_pct", "protein_percent"),
        "carbs": ("carbs", "carbs_pct", "carbs_percent", "carbohydrates"),
        "fat": ("fat", "fat_pct", "fat_percent"),
    }
    normalized: dict[str, float] = {}
    for key, candidates in aliases.items():
        raw = next((value[name] for name in candidates if name in value), None)
        if raw is None:
            raise ValueError("nutrition_target_distribution_must_be_complete")
        normalized[key] = _positive_float(
            raw,
            "nutrition_target_distribution_must_be_positive",
        )
    if abs(sum(normalized.values()) - 100.0) > 0.01:
        raise ValueError("nutrition_target_distribution_must_sum_100")
    fat_percent = normalized["fat"]
    if not MIN_SUPPORTED_FAT_ENERGY_PERCENT <= fat_percent <= MAX_SUPPORTED_FAT_ENERGY_PERCENT:
        raise ValueError("nutrition_target_distribution_fat_out_of_supported_range")
    return normalized


def macro_distribution_from_grams(
    *,
    total_kcal: float,
    protein: float,
    carbs: float,
    fat: float,
) -> dict[str, float]:
    return {
        "protein": protein * PROTEIN_KCAL_PER_GRAM / total_kcal * 100,
        "carbs": carbs * CARBS_KCAL_PER_GRAM / total_kcal * 100,
        "fat": fat * FAT_KCAL_PER_GRAM / total_kcal * 100,
    }


def _validate_resolved_targets(*, energy: float, protein: float, carbs: float, fat: float) -> None:
    if min(protein, carbs, fat) < 0:
        raise ValueError("nutrition_target_macros_must_be_non_negative")
    macro_energy = (
        protein * PROTEIN_KCAL_PER_GRAM
        + carbs * CARBS_KCAL_PER_GRAM
        + fat * FAT_KCAL_PER_GRAM
    )
    if abs(macro_energy - energy) / energy > ENERGY_COHERENCE_TOLERANCE:
        raise ValueError("nutrition_target_macro_energy_conflict")
    fat_percent = fat * FAT_KCAL_PER_GRAM / energy * 100
    if not MIN_SUPPORTED_FAT_ENERGY_PERCENT <= fat_percent <= MAX_SUPPORTED_FAT_ENERGY_PERCENT:
        raise ValueError("nutrition_target_fat_out_of_supported_range")


def _validated_ppk(value: object) -> float:
    ppk = _positive_float(value, "nutrition_target_ppk_must_be_positive")
    if not MIN_SUPPORTED_PROTEIN_PER_KG <= ppk <= MAX_SUPPORTED_PROTEIN_PER_KG:
        raise ValueError("nutrition_target_ppk_out_of_supported_range")
    return ppk


def _validate_derived_ppk(value: float) -> None:
    if not MIN_SUPPORTED_PROTEIN_PER_KG <= value <= MAX_SUPPORTED_PROTEIN_PER_KG:
        raise ValueError("nutrition_target_distribution_ppk_out_of_supported_range")


def _ppk_range_note(value: float) -> str:
    if MIN_PREFERRED_PROTEIN_PER_KG <= value <= MAX_PREFERRED_PROTEIN_PER_KG:
        return "Proteína dentro del rango preferente de 1,6–2,2 g/kg."
    return (
        "Proteína dentro del rango ampliado de 1,0–2,5 g/kg, "
        "pero fuera del rango preferente de 1,6–2,2 g/kg."
    )


def _close_protein_targets(left: float, right: float) -> bool:
    tolerance = max(5.0, abs(right) * ENERGY_COHERENCE_TOLERANCE)
    return abs(left - right) <= tolerance


def _validate_explicit_grams_match_distribution(
    *,
    total_kcal: float,
    distribution: Mapping[str, float],
    protein_target: float | None,
    carb_target: float | None,
    fat_target: float | None,
) -> None:
    """Allow redundant gram targets only when they express the same request.

    Providers commonly translate a user's percentage request to grams before
    invoking the tool. Treating that lossless translation as a competing macro
    mode made valid requests fail. The user's explicit percentage distribution
    remains authoritative; genuinely contradictory gram targets are rejected.
    """

    supplied = {
        "protein": (protein_target, PROTEIN_KCAL_PER_GRAM),
        "carbs": (carb_target, CARBS_KCAL_PER_GRAM),
        "fat": (fat_target, FAT_KCAL_PER_GRAM),
    }
    for macro, (raw_grams, kcal_per_gram) in supplied.items():
        if raw_grams is None:
            continue
        grams = _positive_float(raw_grams, "nutrition_target_macros_must_be_positive")
        actual_percent = grams * kcal_per_gram / total_kcal * 100
        if abs(actual_percent - distribution[macro]) > MACRO_DISTRIBUTION_EQUIVALENCE_TOLERANCE:
            raise ValueError("nutrition_target_macro_modes_conflict")


def _positive_float(value: object, error_code: str) -> float:
    if isinstance(value, bool):
        raise ValueError(error_code)
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(error_code) from exc
    if result <= 0:
        raise ValueError(error_code)
    return result


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def _round_to_step(value: float, step: float) -> float:
    return round(value / step) * step
