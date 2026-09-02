from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Literal

from ninja import Field, Schema


class CalendarizationData(Schema):
    id: int
    source_program_id: int | None = None
    program_name: str
    status: str
    start_date: date
    end_date: date
    timezone_name: str
    progress_day: int
    progress_total_days: int
    progress_percent: int


class MealExecutionData(Schema):
    meal_key: str
    status: str
    last_event_id: int | None = None
    recorded_at: datetime | None = None
    note: str = ""


class AdherenceData(Schema):
    period_start: date
    period_end: date
    days: int
    days_with_plan: int
    scheduled_meals: int
    elapsed_meals: int
    planned_meals: int
    completed_meals: int
    skipped_meals: int
    unrecorded_meals: int
    adherence_percent: int


class MeasurementSummaryData(Schema):
    items: list[dict[str, Any]]
    count: int
    first_weight_kg: float | None = None
    latest_weight_kg: float | None = None
    change_kg: float | None = None


class ReminderEventData(Schema):
    event_key: str
    event_type: str
    meal_key: str
    local_date: date
    local_time: time
    scheduled_for_utc: datetime
    status: str


class ReminderSettingsData(Schema):
    timezone_name: str
    daily_notification_time: time
    daily_notifications_enabled: bool
    meal_notifications_enabled: bool
    upcoming: list[ReminderEventData]


class RevisionDayComparisonData(Schema):
    calendar_date: date
    before_name: str
    after_name: str
    before_totals: dict[str, Any]
    after_totals: dict[str, Any]


class CalendarizationRevisionData(Schema):
    id: int
    effective_from: date
    status: str
    rationale: str
    days: list[RevisionDayComparisonData]
    created_at: datetime


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


class TodayEnvelope(Schema):
    ok: Literal[True] = True
    data: TodayData
    error: None = None


class ActiveProgramDay(Schema):
    id: int
    calendar_date: date
    week_number: int
    day_number: int
    has_plan: bool
    plan_name: str


class ActiveProgramIndicatorData(Schema):
    icon: Literal["food", "dailyPlan", "week"]
    label: str
    value: int | str


class ActiveProgramData(Schema):
    calendarization: CalendarizationData | None = None
    weeks_count: int = 0
    weeks: list[dict[str, Any]] = Field(default_factory=list)
    days: list[ActiveProgramDay]
    adherence: AdherenceData | None = None
    indicators: list[ActiveProgramIndicatorData] = Field(default_factory=list)


class ActiveProgramEnvelope(Schema):
    ok: Literal[True] = True
    data: ActiveProgramData
    error: None = None


class CalendarizationActivationInput(Schema):
    program_id: int = Field(gt=0)
    start_date: date
    timezone_name: str = Field(min_length=1, max_length=64)
    daily_notification_time: time = time(7, 0)
    daily_notifications_enabled: bool = True
    meal_notifications_enabled: bool = False
    confirm_incomplete: bool = False
    replace_current: bool = False


class CalendarizationActivationData(ActiveProgramData):
    empty_dates: list[date] = Field(default_factory=list)
    replaced_calendarization_id: int | None = None


class CalendarizationActivationEnvelope(Schema):
    ok: Literal[True] = True
    data: CalendarizationActivationData
    error: None = None


class CalendarizationHistoryItem(Schema):
    id: int
    program_name: str
    status: str
    start_date: date
    end_date: date
    timezone_name: str
    days_total: int
    days_with_plan: int
    created_at: datetime


class CalendarizationHistoryData(Schema):
    items: list[CalendarizationHistoryItem]
    count: int


class CalendarizationHistoryEnvelope(Schema):
    ok: Literal[True] = True
    data: CalendarizationHistoryData
    error: None = None


class CalendarizedDayDetailData(ActiveProgramDay):
    meal_execution: list[MealExecutionData] = Field(default_factory=list)
    plan_snapshot: dict[str, Any] | None = None


class CalendarizedDayDetailEnvelope(Schema):
    ok: Literal[True] = True
    data: CalendarizedDayDetailData
    error: None = None


class WeightItem(Schema):
    id: int
    measured_on: date
    weight_kg: float
    source: str
    created_at: datetime
    calendarization_id: int | None = None


class WeightListData(Schema):
    items: list[WeightItem]
    count: int


class WeightListEnvelope(Schema):
    ok: Literal[True] = True
    data: WeightListData
    error: None = None


class WeightCreateInput(Schema):
    weight_kg: float = Field(gt=0, le=350)
    measured_on: date | None = None


class WeightEnvelope(Schema):
    ok: Literal[True] = True
    data: WeightItem
    error: None = None


class MealCheckInInput(Schema):
    action: Literal["completed", "skipped", "reset", "note"]
    idempotency_key: str = Field(min_length=8, max_length=120)
    note: str = Field(default="", max_length=500)


class ReminderSettingsInput(Schema):
    timezone_name: str = Field(min_length=1, max_length=64)
    daily_notification_time: time
    daily_notifications_enabled: bool
    meal_notifications_enabled: bool


class ApplePushRegistrationInput(Schema):
    device_token: str = Field(min_length=32, max_length=220)
    environment: Literal["sandbox", "production"]


class ApplePushRegistrationData(Schema):
    delivery_mode: Literal["apns", "local"]
    token_fingerprint: str
    environment: Literal["sandbox", "production"]
    is_active: bool


class ApplePushRegistrationEnvelope(Schema):
    ok: Literal[True] = True
    data: ApplePushRegistrationData
    error: None = None


class CalendarizationReviewInput(Schema):
    period_start: date
    period_end: date
    idempotency_key: str = Field(min_length=8, max_length=120)
    energy_score: int | None = Field(default=None, ge=1, le=5)
    hunger_score: int | None = Field(default=None, ge=1, le=5)
    training_performance_score: int | None = Field(default=None, ge=1, le=5)
    note: str = Field(default="", max_length=1000)


class CalendarizationReviewData(Schema):
    id: int
    period_start: date
    period_end: date
    energy_score: int | None = None
    hunger_score: int | None = None
    training_performance_score: int | None = None
    note: str
    summary_snapshot: dict[str, Any]
    created_at: datetime


class CalendarizationReviewListData(Schema):
    items: list[CalendarizationReviewData]
    count: int


class CalendarizationReviewEnvelope(Schema):
    ok: Literal[True] = True
    data: CalendarizationReviewData
    error: None = None


class CalendarizationReviewListEnvelope(Schema):
    ok: Literal[True] = True
    data: CalendarizationReviewListData
    error: None = None


class ReminderSettingsEnvelope(Schema):
    ok: Literal[True] = True
    data: ReminderSettingsData
    error: None = None


class RevisionListData(Schema):
    items: list[CalendarizationRevisionData]
    count: int


class RevisionListEnvelope(Schema):
    ok: Literal[True] = True
    data: RevisionListData
    error: None = None


class RevisionDecisionInput(Schema):
    decision: Literal["approve", "reject"]


class RevisionEnvelope(Schema):
    ok: Literal[True] = True
    data: CalendarizationRevisionData
    error: None = None
