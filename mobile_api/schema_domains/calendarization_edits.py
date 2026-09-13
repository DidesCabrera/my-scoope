from __future__ import annotations

from datetime import time

from ninja import Field, Schema


class CalendarizedMealHourInput(Schema):
    hour: time


class CalendarizedNameInput(Schema):
    name: str = Field(min_length=1, max_length=255)


class CalendarizedDayPlanPreviewInput(Schema):
    dailyplan_id: int = Field(gt=0)


class CalendarizedDayPlanCommitInput(CalendarizedDayPlanPreviewInput):
    idempotency_key: str = Field(min_length=8, max_length=120)
    confirm_replacement: bool = False


class CalendarizedMealPickerInput(Schema):
    meal_id: int = Field(gt=0)
    meal_snapshot_key: str | None = Field(default=None, min_length=1, max_length=80)
    hour: time | None = None
    note: str = Field(default="", max_length=500)


class CalendarizedFoodPickerInput(Schema):
    food_id: int = Field(gt=0)
    food_snapshot_key: str | None = Field(default=None, min_length=1, max_length=80)
    quantity: float = Field(gt=0, le=100000)


class CalendarizedOrderInput(Schema):
    ordered_keys: list[str] = Field(min_length=1)


class CalendarizedFoodQuantityInput(Schema):
    quantity: float = Field(gt=0, le=100000)
