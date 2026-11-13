from typing import Literal

from ninja import Field, Schema


class FoodCreateInput(Schema):
    name: str = Field(min_length=1, max_length=100)
    protein: float = Field(ge=0, le=100)
    carbs: float = Field(ge=0, le=100)
    fat: float = Field(ge=0, le=100)
    saturated_fat_g: float | None = Field(default=None, ge=0, le=100)
    sugar_g: float | None = Field(default=None, ge=0, le=100)
    fiber_g: float | None = Field(default=None, ge=0, le=100)
    sodium_mg: float | None = Field(default=None, ge=0, le=100_000)
    portion_unit: Literal["g", "ml"] = "g"


