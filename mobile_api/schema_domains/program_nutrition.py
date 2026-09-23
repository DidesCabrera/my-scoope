"""Weekly nutrition requirements exposed in reviewable program proposals."""

from typing import Literal

from ninja import Schema


class ProgramWeekTargetData(Schema):
    week: int
    kcal: float
    projected_weight_kg: float | None = None
    reference_weight_kg: float
    protein_min_g: float
    protein_max_g: float


class ProgramNutritionSpecificationData(Schema):
    version: int
    duration_weeks: int
    meals_per_day: int
    weight_basis: Literal["measured", "projected"]
    measured_weight_kg: float
    protein_min_ppk: float
    protein_max_ppk: float
    fat_max_percent: float
    calorie_tolerance_percent: float
    weeks: list[ProgramWeekTargetData]
