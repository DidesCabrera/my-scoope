from __future__ import annotations

from typing import Literal

from ninja import Field, Schema

from mobile_api.schema_domains.libraries import LibraryIndicatorData, LibraryNutritionData, LibraryPanelData


class PickerSelectionData(Schema):
    id: int
    entity: Literal["food", "meal", "dailyPlan", "week"]
    name: str
    nutrition: LibraryNutritionData | None = None
    quantity: float | None = None
    hour: str | None = None


class PickerMetricData(Schema):
    label: str
    before: float
    after: float


class PickerImpactData(Schema):
    label: str
    entity: Literal["meal", "dailyPlan", "week", "program"]
    before: LibraryNutritionData
    after: LibraryNutritionData
    metrics: list[PickerMetricData] = Field(default_factory=list)


class PickerResultData(Schema):
    id: int
    entity: Literal["meal", "dailyPlan", "week"]
    name: str
    nutrition: LibraryNutritionData
    indicators: list[LibraryIndicatorData] = Field(default_factory=list)
    panel: LibraryPanelData


class PickerPreviewData(Schema):
    selection: PickerSelectionData
    impacts: list[PickerImpactData]
    result: PickerResultData | None = None
    replacements: list[str] = Field(default_factory=list)
    confirmation_required: bool = False


class PickerPreviewEnvelope(Schema):
    ok: Literal[True] = True
    data: PickerPreviewData
    error: None = None
