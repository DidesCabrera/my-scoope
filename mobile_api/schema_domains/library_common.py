from typing import Literal

from ninja import Schema


class OptionalPortionUnitData(Schema):
    quantity_unit: Literal["g", "ml"] | None = None


class FoodNutritionFactsData(Schema):
    saturated_fat_g: float | None = None
    sugar_g: float | None = None
    fiber_g: float | None = None
    sodium_mg: float | None = None
