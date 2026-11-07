from typing import Literal

from ninja import Field, Schema


class OptionalPortionUnitData(Schema):
    quantity_unit: Literal["g", "ml"] | None = None


class FoodVisualIdentityData(Schema):
    emoji: str = ""
    visual_key: str = ""


class FoodPortionContractData(Schema):
    default_portion: float | None = None
    household_amount: float | None = None
    household_measure: str = ""
    household_measure_label: str = ""
    household_detail: str = ""
    myscoope_group: str = ""
    myscoope_group_label: str = ""


class OptionalFoodVisualIdentityData(Schema):
    emoji: str | None = None
    visual_key: str | None = None


class SupplementLibraryAccessData(Schema):
    can_use_supplements: bool = False
    supplements_available: bool = False


class SupplementLibraryPanelData(Schema):
    supplement_intakes: list[dict] = Field(default_factory=list)


class LibraryMacroData(Schema):
    grams: float
    allocation: float
    per_kilogram: float | None = None


class FoodNutritionFactsData(Schema):
    saturated_fat_g: float | None = None
    sugar_g: float | None = None
    fiber_g: float | None = None
    sodium_mg: float | None = None
