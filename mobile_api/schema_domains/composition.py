from __future__ import annotations

from datetime import time
from typing import Literal

from ninja import Field, Schema


class FoodPickerInput(Schema):
    food_id: int = Field(gt=0)
    meal_food_id: int | None = Field(default=None, gt=0)
    dailyplan_id: int | None = Field(default=None, gt=0)
    dailyplan_meal_id: int | None = Field(default=None, gt=0)
    quantity: float = Field(gt=0, le=100000)


class MealPickerInput(Schema):
    meal_id: int = Field(gt=0)
    dailyplan_meal_id: int | None = Field(default=None, gt=0)
    hour: time | None = None
    note: str = Field(default="", max_length=500)


class CompositionOrderInput(Schema):
    ordered_ids: list[int] = Field(min_length=1)


class MealFoodUpdateInput(Schema):
    quantity: float = Field(gt=0, le=100000)


class DailyPlanMealUpdateInput(Schema):
    hour: time | None = None
    note: str | None = Field(default=None, max_length=500)


class CompositionMutationData(Schema):
    message: str
    target_id: int
    affected_id: int


class CompositionMutationEnvelope(Schema):
    ok: Literal[True] = True
    data: CompositionMutationData
    error: None = None


class DailyPlanPickerInput(Schema):
    dailyplan_id: int = Field(gt=0)
    week_number: int = Field(gt=0)
    day_numbers: list[int] = Field(min_length=1, max_length=7)
    confirm_replacements: bool = False


class PickerCommitData(Schema):
    message: str
    target_id: int
    created_id: int


class PickerCommitEnvelope(Schema):
    ok: Literal[True] = True
    data: PickerCommitData
    error: None = None
