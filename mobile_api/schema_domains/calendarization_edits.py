from __future__ import annotations

from datetime import time

from ninja import Field, Schema


class CalendarizedMealHourInput(Schema):
    hour: time


class CalendarizedNameInput(Schema):
    name: str = Field(min_length=1, max_length=255)
