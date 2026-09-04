from __future__ import annotations

from datetime import datetime
from typing import Literal

from ninja import Field, Schema


class FoodItem(Schema):
    id: int
    name: str
    display_name: str
    protein: float
    carbs: float
    fat: float
    total_kcal: float
    protein_allocation: float
    carbs_allocation: float
    fat_allocation: float
    source: str
    is_user_food: bool
    is_verified: bool
    data_quality_score: int


class FoodPageData(Schema):
    items: list[FoodItem]
    total: int
    offset: int
    limit: int
    search: str | None = None


class FoodPageEnvelope(Schema):
    ok: Literal[True] = True
    data: FoodPageData
    error: None = None


class FoodItemEnvelope(Schema):
    ok: Literal[True] = True
    data: FoodItem
    error: None = None


class LibraryMacroData(Schema):
    grams: float
    allocation: float
    per_kilogram: float | None = None


class LibraryNutritionData(Schema):
    calories: float
    protein: LibraryMacroData
    carbs: LibraryMacroData
    fat: LibraryMacroData


class LibraryIndicatorData(Schema):
    icon: Literal["day", "food", "meal", "dailyPlan", "week"] | None = None
    label: str
    value: int | str


class LibraryCalorieDistributionData(Schema):
    protein: float
    carbs: float
    fat: float


class LibraryFoodPanelItemData(Schema):
    id: str
    relation_id: int | None = None
    name: str
    quantity: float
    quantity_unit: str
    calories: float
    calorie_share: float
    calorie_distribution: LibraryCalorieDistributionData
    protein_grams: float
    carbs_grams: float
    fat_grams: float
    protein_allocation: float
    carbs_allocation: float
    fat_allocation: float


class LibraryMealPanelItemData(Schema):
    id: str
    relation_id: int | None = None
    detail_id: int
    name: str
    time: str | None = None
    note: str = ""
    foods: list[LibraryFoodPanelItemData]
    calories: float
    calorie_share: float
    calorie_distribution: LibraryCalorieDistributionData
    protein_grams: float
    protein_per_kilogram: float | None = None
    carbs_grams: float
    fat_grams: float
    protein_allocation: float
    carbs_allocation: float
    fat_allocation: float


class LibraryWeekDayData(Schema):
    id: str
    program_day_id: int | None = None
    day_number: int
    day_label: str
    dailyplan_id: int | None = None
    plan_name: str | None = None
    nutrition: LibraryNutritionData | None = None
    meals: list[LibraryMealPanelItemData] = Field(default_factory=list)


class LibraryWeekPanelItemData(Schema):
    id: str
    week_number: int
    days: list[LibraryWeekDayData]
    filled_days_count: int
    meals_count: int
    foods_count: int
    average_calories: float
    foods: list[LibraryFoodPanelItemData] = Field(default_factory=list)
    calories: float
    calorie_share: float
    calorie_distribution: LibraryCalorieDistributionData
    protein_grams: float
    carbs_grams: float
    fat_grams: float
    protein_allocation: float
    carbs_allocation: float
    fat_allocation: float


class LibraryPanelData(Schema):
    kind: Literal["none", "foods", "meals", "weeks"]
    foods: list[LibraryFoodPanelItemData] = Field(default_factory=list)
    meals: list[LibraryMealPanelItemData] = Field(default_factory=list)
    weeks: list[LibraryWeekPanelItemData] = Field(default_factory=list)


class LibraryActionData(Schema):
    key: Literal["rename", "duplicate", "share", "delete"]
    label: str
    destructive: bool = False


class FoodCreateInput(Schema):
    name: str = Field(min_length=1, max_length=100)
    protein: float = Field(ge=0, le=100)
    carbs: float = Field(ge=0, le=100)
    fat: float = Field(ge=0, le=100)


class NamedLibraryCreateInput(Schema):
    name: str = Field(min_length=1, max_length=100)


class LibraryItemData(Schema):
    id: int
    entity: Literal["food", "meal", "dailyPlan", "program"]
    name: str
    subtitle: str
    nutrition: LibraryNutritionData
    indicators: list[LibraryIndicatorData]
    panel: LibraryPanelData
    creator: str
    created_at: datetime
    is_draft: bool = False
    can_calendarize: bool = False
    actions: list[LibraryActionData] = Field(default_factory=list)
    label_capture_receipt_id: int | None = None
    label_image_available: bool = False


class LibraryPageData(Schema):
    items: list[LibraryItemData]
    total: int
    offset: int
    limit: int
    search: str | None = None


class LibraryPageEnvelope(Schema):
    ok: Literal[True] = True
    data: LibraryPageData
    error: None = None


class LibraryItemEnvelope(Schema):
    ok: Literal[True] = True
    data: LibraryItemData
    error: None = None


class LibraryActionInput(Schema):
    action: Literal["rename", "duplicate", "share", "delete"]
    name: str = Field(default="", max_length=100)
    recipient_email: str = Field(default="", max_length=254)
    subject: str = Field(default="", max_length=160)
    message: str = Field(default="", max_length=2000)


class LibraryActionResultData(Schema):
    action: Literal["rename", "duplicate", "share", "delete"]
    item_id: int
    message: str


class LibraryActionResultEnvelope(Schema):
    ok: Literal[True] = True
    data: LibraryActionResultData
    error: None = None


class LibraryOrderInput(Schema):
    ordered_ids: list[int] = Field(min_length=1)


class LibraryBulkDeleteInput(Schema):
    item_ids: list[int] = Field(min_length=1)


class LibraryListActionResultData(Schema):
    affected_ids: list[int]
    skipped_ids: list[int] = Field(default_factory=list)
    message: str


class LibraryListActionResultEnvelope(Schema):
    ok: Literal[True] = True
    data: LibraryListActionResultData
    error: None = None
