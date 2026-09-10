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
