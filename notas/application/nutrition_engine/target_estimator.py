from __future__ import annotations

from dataclasses import dataclass

from notas.domain.constants.nutrition import (
    CARBS_KCAL_PER_GRAM,
    FAT_KCAL_PER_GRAM,
    PROTEIN_KCAL_PER_GRAM,
)


DEFAULT_CALORIE_TARGET = 2200
DEFAULT_PROTEIN_TARGET = 140
DEFAULT_CURRENT_WEIGHT_KG = 75

MIN_ESTIMATED_CALORIE_TARGET = 1600
MAX_ESTIMATED_CALORIE_TARGET = 3600
MIN_ESTIMATED_PROTEIN_TARGET = 90
MAX_ESTIMATED_PROTEIN_TARGET = 230
MIN_ESTIMATED_FAT_TARGET = 40
MAX_ESTIMATED_FAT_TARGET = 110

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "high": 1.725,
    "very_high": 1.9,
}

ENERGY_ADJUSTMENT_FACTORS = {
    "deficit_mild": -0.10,
    "deficit_moderate": -0.15,
    "deficit_large": -0.22,
    "surplus_mild": 0.08,
    "surplus_moderate": 0.12,
    "surplus_large": 0.18,
    "maintenance": 0.0,
}

DEFAULT_ENERGY_ADJUSTMENT_BY_GOAL = {
    "fat_loss": "deficit_moderate",
    "muscle_gain": "surplus_mild",
    "maintenance": "maintenance",
    "performance": "surplus_mild",
    "healthy_eating": "maintenance",
}

PROTEIN_PER_KG_BY_GOAL = {
    "fat_loss": 1.8,
    "muscle_gain": 1.8,
    "maintenance": 1.5,
    "performance": 1.6,
    "healthy_eating": 1.5,
}


@dataclass(frozen=True)
class TargetEstimationProfile:
    """Input contract for estimating daily energy and macro targets.

    This class keeps target estimation independent from the chat/intake UI. Any
    caller can build one from a NutritionBrief, profile settings, MCP payload, or
    another internal workflow.
    """

    goal: str | None = None
    weight_kg: float | None = None
    height_cm: int | None = None
    age_years: int | None = None
    sex: str | None = None
    activity_level: str | None = None
    energy_adjustment: str | None = None
    calorie_target: int | None = None
    protein_target: int | None = None
    carb_target: int | None = None
    fat_target: int | None = None
    subject_source: str | None = None
    ppk_weight_source: str | None = None
    requires_library_ppk_warning: bool = False


@dataclass(frozen=True)
class EnergyExpenditureEstimate:
    bmr: float | None
    tdee: float | None
    method: str
    activity_factor: float | None
    notes: list[str]

    def as_dict(self) -> dict:
        return {
            "bmr": round(self.bmr, 2) if self.bmr is not None else None,
            "tdee": round(self.tdee, 2) if self.tdee is not None else None,
            "method": self.method,
            "activity_factor": round(self.activity_factor, 3) if self.activity_factor is not None else None,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class DailyNutritionTargetPlan:
    total_kcal: float
    protein: float
    carbs: float
    fat: float
    weight_kg: float
    estimated_bmr: float | None
    estimated_tdee: float | None
    energy_adjustment: str
    energy_adjustment_factor: float
    explicit_targets: dict[str, bool]
    estimated_targets: dict[str, bool]
    notes: list[str]
    protein_per_kg: float
    estimated_maintenance_kcal: float | None
    target_kcal_before_rounding: float | None
    estimation_method: str
    energy_expenditure: EnergyExpenditureEstimate
    subject_source: str | None = None
    ppk_weight_source: str | None = None
    requires_library_ppk_warning: bool = False

    def as_targets_dict(self) -> dict:
        return {
            "total_kcal": round(self.total_kcal, 2),
            "protein": round(self.protein, 2),
            "carbs": round(self.carbs, 2),
            "fat": round(self.fat, 2),
            "weight_kg": round(self.weight_kg, 2),
            "estimated_bmr": round(self.estimated_bmr, 2) if self.estimated_bmr is not None else None,
            "estimated_tdee": round(self.estimated_tdee, 2) if self.estimated_tdee is not None else None,
            "estimated_maintenance_kcal": (
                round(self.estimated_maintenance_kcal, 2) if self.estimated_maintenance_kcal is not None else None
            ),
            "target_kcal_before_rounding": (
                round(self.target_kcal_before_rounding, 2) if self.target_kcal_before_rounding is not None else None
            ),
            "energy_adjustment": self.energy_adjustment,
            "energy_adjustment_factor": round(self.energy_adjustment_factor, 4),
            "protein_per_kg": round(self.protein_per_kg, 2),
            "estimation_method": self.estimation_method,
            "explicit_targets": dict(self.explicit_targets),
            "estimated_targets": dict(self.estimated_targets),
            "energy_expenditure": self.energy_expenditure.as_dict(),
            "subject_context": {
                "source": self.subject_source,
                "ppk_weight_source": self.ppk_weight_source,
                "requires_library_ppk_warning": self.requires_library_ppk_warning,
                "calculation_weight_kg": round(self.weight_kg, 2),
            },
            "notes": list(self.notes),
        }


def estimate_daily_targets(profile: TargetEstimationProfile) -> DailyNutritionTargetPlan:
    """Estimate a daily kcal/macros target from user/body inputs.

    Explicit targets always win. Missing targets are estimated from BMR/TDEE
    whenever possible and otherwise fall back to conservative defaults.
    """

    weight_kg = _safe_weight(profile.weight_kg)
    goal = profile.goal or "healthy_eating"
    expenditure = estimate_energy_expenditure(profile=profile, weight_kg=weight_kg)
    energy_adjustment = resolve_energy_adjustment(goal=goal, requested_adjustment=profile.energy_adjustment)
    energy_adjustment_factor = ENERGY_ADJUSTMENT_FACTORS.get(energy_adjustment, 0.0)

    target_kcal_before_rounding = None
    if expenditure.tdee is not None:
        target_kcal_before_rounding = expenditure.tdee * (1 + energy_adjustment_factor)
        inferred_kcal = _round_to_step(
            _clamp(
                target_kcal_before_rounding,
                MIN_ESTIMATED_CALORIE_TARGET,
                MAX_ESTIMATED_CALORIE_TARGET,
            ),
            25,
        )
        estimation_method = "mifflin_st_jeor_tdee_adjusted"
    else:
        inferred_kcal = DEFAULT_CALORIE_TARGET
        estimation_method = "default_target_without_full_expenditure_inputs"

    total_kcal = float(profile.calorie_target or inferred_kcal or DEFAULT_CALORIE_TARGET)

    protein_per_kg = PROTEIN_PER_KG_BY_GOAL.get(goal, PROTEIN_PER_KG_BY_GOAL["healthy_eating"])
    inferred_protein = _round_to_step(
        _clamp(
            weight_kg * protein_per_kg,
            MIN_ESTIMATED_PROTEIN_TARGET,
            MAX_ESTIMATED_PROTEIN_TARGET,
        ),
        5,
    )
    protein = float(profile.protein_target or inferred_protein or DEFAULT_PROTEIN_TARGET)

    remaining_after_protein = total_kcal - protein * PROTEIN_KCAL_PER_GRAM
    default_fat = _round_to_step(
        _clamp(
            total_kcal * 0.25 / FAT_KCAL_PER_GRAM,
            MIN_ESTIMATED_FAT_TARGET,
            MAX_ESTIMATED_FAT_TARGET,
        ),
        5,
    )

    if profile.fat_target is not None:
        fat = float(profile.fat_target)
    elif profile.carb_target is not None:
        fat = _round_to_step(
            max(0.0, (remaining_after_protein - profile.carb_target * CARBS_KCAL_PER_GRAM) / FAT_KCAL_PER_GRAM),
            5,
        )
    else:
        fat = float(default_fat)

    if profile.carb_target is not None:
        carbs = float(profile.carb_target)
    else:
        carbs = _round_to_step(
            max(0.0, (total_kcal - protein * PROTEIN_KCAL_PER_GRAM - fat * FAT_KCAL_PER_GRAM) / CARBS_KCAL_PER_GRAM),
            5,
        )

    notes = _build_target_notes(
        profile=profile,
        expenditure=expenditure,
        total_kcal=total_kcal,
        protein=protein,
        carbs=carbs,
        fat=fat,
    )

    return DailyNutritionTargetPlan(
        total_kcal=float(total_kcal),
        protein=float(protein),
        carbs=float(carbs),
        fat=float(fat),
        weight_kg=float(weight_kg),
        estimated_bmr=float(expenditure.bmr) if expenditure.bmr is not None else None,
        estimated_tdee=float(expenditure.tdee) if expenditure.tdee is not None else None,
        energy_adjustment=energy_adjustment,
        energy_adjustment_factor=float(energy_adjustment_factor),
        explicit_targets={
            "total_kcal": profile.calorie_target is not None,
            "protein": profile.protein_target is not None,
            "carbs": profile.carb_target is not None,
            "fat": profile.fat_target is not None,
        },
        estimated_targets={
            "total_kcal": profile.calorie_target is None,
            "protein": profile.protein_target is None,
            "carbs": profile.carb_target is None,
            "fat": profile.fat_target is None,
        },
        notes=notes,
        protein_per_kg=float(protein_per_kg),
        estimated_maintenance_kcal=float(expenditure.tdee) if expenditure.tdee is not None else None,
        target_kcal_before_rounding=(
            float(target_kcal_before_rounding) if target_kcal_before_rounding is not None else None
        ),
        estimation_method=estimation_method,
        energy_expenditure=expenditure,
        subject_source=profile.subject_source,
        ppk_weight_source=profile.ppk_weight_source,
        requires_library_ppk_warning=bool(profile.requires_library_ppk_warning),
    )


def estimate_energy_expenditure(
    *,
    profile: TargetEstimationProfile,
    weight_kg: float | None = None,
) -> EnergyExpenditureEstimate:
    normalized_weight = _safe_weight(weight_kg if weight_kg is not None else profile.weight_kg)
    bmr = estimate_bmr_mifflin_st_jeor(
        weight_kg=normalized_weight,
        height_cm=profile.height_cm,
        age_years=profile.age_years,
        sex=profile.sex,
    )
    notes = []

    if bmr is None:
        notes.append("No se pudo estimar BMR: faltan altura, edad o sexo.")
        return EnergyExpenditureEstimate(
            bmr=None,
            tdee=None,
            method="insufficient_inputs",
            activity_factor=None,
            notes=notes,
        )

    if not profile.activity_level:
        notes.append("No se pudo estimar TDEE: falta nivel de actividad.")
        return EnergyExpenditureEstimate(
            bmr=bmr,
            tdee=None,
            method="mifflin_st_jeor_without_activity",
            activity_factor=None,
            notes=notes,
        )

    activity_factor = ACTIVITY_FACTORS.get(profile.activity_level, ACTIVITY_FACTORS["moderate"])
    return EnergyExpenditureEstimate(
        bmr=bmr,
        tdee=bmr * activity_factor,
        method="mifflin_st_jeor",
        activity_factor=activity_factor,
        notes=["BMR estimado con Mifflin-St Jeor y TDEE con factor de actividad."],
    )


def estimate_bmr_mifflin_st_jeor(
    *,
    weight_kg: float,
    height_cm: int | None,
    age_years: int | None,
    sex: str | None,
) -> float | None:
    if not (height_cm and age_years and sex):
        return None

    sex_constant = 5 if sex == "male" else -161
    return (
        10 * float(weight_kg)
        + 6.25 * float(height_cm)
        - 5 * float(age_years)
        + sex_constant
    )


def resolve_energy_adjustment(*, goal: str | None, requested_adjustment: str | None = None) -> str:
    if requested_adjustment:
        return requested_adjustment

    return DEFAULT_ENERGY_ADJUSTMENT_BY_GOAL.get(
        goal or "healthy_eating",
        DEFAULT_ENERGY_ADJUSTMENT_BY_GOAL["healthy_eating"],
    )


def _build_target_notes(
    *,
    profile: TargetEstimationProfile,
    expenditure: EnergyExpenditureEstimate,
    total_kcal: float,
    protein: float,
    carbs: float,
    fat: float,
) -> list[str]:
    notes = [
        "Targets generados por el Target Estimator del motor nutricional.",
    ]

    if profile.calorie_target is None:
        if expenditure.tdee is not None:
            notes.append("Kcal estimadas desde BMR/TDEE y ajuste energético del brief.")
        else:
            notes.append("Kcal estimadas con fallback por falta de datos completos de gasto energético.")

    if profile.protein_target is None:
        notes.append("Proteína estimada según peso actual y objetivo nutricional.")

    if profile.carb_target is None or profile.fat_target is None:
        notes.append("Carbohidratos y grasas distribuidos desde kcal/proteína con una heurística inicial.")

    macro_kcal = protein * PROTEIN_KCAL_PER_GRAM + carbs * CARBS_KCAL_PER_GRAM + fat * FAT_KCAL_PER_GRAM
    if abs(macro_kcal - total_kcal) > 75:
        notes.append("Los macros estimados no calzan perfectamente con las kcal por redondeos o targets explícitos.")

    return notes


def _safe_weight(value) -> float:
    try:
        weight = float(value)
    except (TypeError, ValueError):
        weight = DEFAULT_CURRENT_WEIGHT_KG

    return _clamp(weight, 35, 180)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(float(value), maximum))


def _round_to_step(value: float, step: float) -> float:
    step = step or 5
    return float(round(float(value) / step) * step)
