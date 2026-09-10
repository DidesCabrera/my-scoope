from __future__ import annotations

from ninja import Field, Schema


class ProposalKpisData(Schema):
    total_kcal: float | None = None
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None
    ppk: float | None = None
    alloc_protein: float | None = None
    alloc_carbs: float | None = None
    alloc_fat: float | None = None


class ProposalFoodData(Schema):
    food_id: int | None = None
    food_name: str
    quantity: float | None = None
    unit: str = "g"
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None
    total_kcal: float | None = None


class ProposalMealData(Schema):
    name: str
    foods: list[ProposalFoodData] = Field(default_factory=list)
    kpis: ProposalKpisData | None = None


class ProposalDailyPlanMealData(Schema):
    hour: str | None = None
    note: str = ""
    meal: ProposalMealData


class ProposalDailyPlanData(Schema):
    name: str
    meals: list[ProposalDailyPlanMealData] = Field(default_factory=list)
    kpis: ProposalKpisData | None = None
