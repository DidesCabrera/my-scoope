from __future__ import annotations

from datetime import datetime
from typing import Literal

from ninja import Field, Schema


class ComparisonKindData(Schema):
    key: Literal["foods", "meals", "dailyplans"]
    label: str
    entity_label: str
    uses_quantity: bool
    quantity_unit: str | None = None
    includes_ppk: bool


class ComparisonMetadataData(Schema):
    kinds: list[ComparisonKindData]


class ComparisonMetadataEnvelope(Schema):
    ok: Literal[True] = True
    data: ComparisonMetadataData
    error: None = None


class ComparisonSelectionInput(Schema):
    id: int = Field(gt=0)
    quantity: float | None = None


class ComparisonRequestInput(Schema):
    kind: Literal["foods", "meals", "dailyplans"]
    selections: list[ComparisonSelectionInput] = Field(min_length=2)


class ComparisonMetricValuesData(Schema):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    protein_per_kilogram: float | None = None


class ComparisonMetricBarData(Schema):
    position: int
    id: int
    label: str
    quantity: float | None = None
    value: float
    formatted_value: str
    relative_percentage: float


class ComparisonMetricData(Schema):
    key: Literal["total_kcal", "ppk", "protein", "carbs", "fat", "alloc_protein", "alloc_carbs", "alloc_fat"]
    label: str
    unit: str
    bars: list[ComparisonMetricBarData]


class ComparisonResultItemData(Schema):
    position: int
    id: int
    name: str
    quantity: float | None = None
    values: ComparisonMetricValuesData


class ComparisonResultData(Schema):
    kind: Literal["foods", "meals", "dailyplans"]
    kind_label: str
    historical_snapshot: bool = False
    saved_comparison_id: int | None = None
    saved_comparison_name: str = ""
    metrics: list[ComparisonMetricData]
    items: list[ComparisonResultItemData]


class ComparisonResultEnvelope(Schema):
    ok: Literal[True] = True
    data: ComparisonResultData
    error: None = None


class SavedComparisonSummaryData(Schema):
    id: int
    name: str
    kind: Literal["foods", "meals", "dailyplans"]
    kind_label: str
    item_count: int
    updated_at: datetime


class SavedComparisonListData(Schema):
    items: list[SavedComparisonSummaryData]
    total: int
    offset: int
    limit: int


class SavedComparisonListEnvelope(Schema):
    ok: Literal[True] = True
    data: SavedComparisonListData
    error: None = None


class SavedComparisonDetailData(ComparisonResultData):
    editable_selections: list[ComparisonSelectionInput]
    updated_at: datetime


class SavedComparisonDetailEnvelope(Schema):
    ok: Literal[True] = True
    data: SavedComparisonDetailData
    error: None = None
