from typing import Literal

from ninja import Schema

from mobile_api.schema_domains.libraries import LibraryItemData


Occasion = Literal["breakfast", "lunch", "dinner", "snack", "pre_workout", "post_workout"]
DietaryStyle = Literal["omnivore", "pescatarian", "vegetarian", "vegan"]


class ExploreMealItemData(LibraryItemData):
    catalog_id: int
    summary: str
    occasion: Occasion
    occasion_label: str
    dietary_style: DietaryStyle
    dietary_style_label: str
    is_saved: bool


class ExploreMealPageData(Schema):
    items: list[ExploreMealItemData]
    total: int
    offset: int
    limit: int
    search: str | None = None


class ExploreMealPageEnvelope(Schema):
    ok: Literal[True] = True
    data: ExploreMealPageData
    error: None = None


class ExploreMealItemEnvelope(Schema):
    ok: Literal[True] = True
    data: ExploreMealItemData
    error: None = None


class ExploreMealSaveResultData(Schema):
    saved_meal_id: int
    already_saved: bool
    message: str


class ExploreMealSaveResultEnvelope(Schema):
    ok: Literal[True] = True
    data: ExploreMealSaveResultData
    error: None = None

