from datetime import date
from typing import Any, Literal

from ninja import Field, Schema

from mobile_api.schema_domains.calendarization import (
    AdherenceData,
    CalendarizationData,
    CalendarizationRevisionData,
    MealExecutionData,
    MeasurementSummaryData,
    ReminderSettingsData,
)
from mobile_api.schema_domains.libraries import LibraryItemData


class TodayData(Schema):
    local_date: date
    calendarization: CalendarizationData | None = None
    day_id: int | None = None
    has_plan: bool
    plan_snapshot: dict[str, Any] | None = None
    meal_execution: list[MealExecutionData] = Field(default_factory=list)
    adherence: AdherenceData | None = None
    measurements: MeasurementSummaryData | None = None
    reminders: ReminderSettingsData | None = None
    pending_revision: CalendarizationRevisionData | None = None
    pinned_plan: LibraryItemData | None = None


class PinnedDailyPlanInput(Schema):
    dailyplan_id: int = Field(gt=0)


class TodayEnvelope(Schema):
    ok: Literal[True] = True
    data: TodayData
    error: None = None
