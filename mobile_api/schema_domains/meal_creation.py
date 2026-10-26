from typing import Literal

from ninja import Field, Schema


class MealCreateInput(Schema):
    name: str = Field(min_length=1, max_length=100)
    meal_type: Literal["breakfast", "snack", "lunch", "shake", "dinner"] | None = None
