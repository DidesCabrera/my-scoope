from typing import Literal

from ninja import Schema


class LibraryPreparationIngredientData(Schema):
    food_id: int
    name: str
    quantity_g: float
    preparation_state: str
    is_condiment: bool


class LibraryPreparationPanelItemData(Schema):
    relation_id: int
    detail_id: int
    name: str
    version: int
    quantity_g: float
    selected_units: float | None = None
    selection_mode: Literal["units", "grams"]
    household_label: str
    calories: float
    sodium_mg: float | None = None
    allergens: list[str]
    ingredients: list[LibraryPreparationIngredientData]
