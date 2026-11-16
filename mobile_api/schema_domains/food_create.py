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
    default_portion: float | None = Field(default=None, gt=0, le=99999)
    household_amount: float | None = Field(default=None, gt=0, le=99999)
    household_measure: Literal["", "unit", "cup", "tablespoon", "scoop", "other", "slice", "can", "fillet", "leaf", "strip", "g", "ml"] = ""
    household_detail: str = Field(default="", max_length=160)
