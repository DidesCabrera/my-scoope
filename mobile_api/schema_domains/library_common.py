from typing import Literal

from ninja import Schema


class OptionalPortionUnitData(Schema):
    quantity_unit: Literal["g", "ml"] | None = None


class FoodVisualIdentityData(Schema):
    emoji: str = ""
    visual_key: str = ""


class OptionalFoodVisualIdentityData(Schema):
    emoji: str | None = None
    visual_key: str | None = None


class LibraryMacroData(Schema):
    grams: float
    allocation: float
    per_kilogram: float | None = None


class FoodNutritionFactsData(Schema):
    saturated_fat_g: float | None = None
    sugar_g: float | None = None
    fiber_g: float | None = None
    sodium_mg: float | None = None
