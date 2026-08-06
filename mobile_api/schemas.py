from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Literal

from ninja import Field, Schema


class ErrorDetail(Schema):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(Schema):
    ok: Literal[False] = False
    data: dict[str, Any] = Field(default_factory=dict)
    error: ErrorDetail


class HealthData(Schema):
    status: str
    api_version: str


class HealthEnvelope(Schema):
    ok: Literal[True] = True
    data: HealthData
    error: None = None


class SessionData(Schema):
    user_id: int
    username: str
    email: str
    display_name: str
    scopes: list[str]
    device_session_id: str | None = None


class SessionEnvelope(Schema):
    ok: Literal[True] = True
    data: SessionData
    error: None = None


class ProfileData(Schema):
    birth_date: date | None = None
    sex: str
    height_cm: int | None = None
    timezone_name: str
    onboarding_completed: bool
    onboarding_version: int
    current_weight_kg: float | None = None


class ProfileEnvelope(Schema):
    ok: Literal[True] = True
    data: ProfileData
    error: None = None


class EntitlementsData(Schema):
    plan_name: str
    plan_slug: str
    subscription_status: str
    period: str
    available_credits: int
    reserved_credits: int
    monthly_credit_limit: int
    daily_credit_limit: int


class EntitlementsEnvelope(Schema):
    ok: Literal[True] = True
    data: EntitlementsData
    error: None = None


class CalendarizationData(Schema):
    id: int
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
    event_type: str
    meal_key: str
    local_date: date
    local_time: time
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


class ActiveProgramData(Schema):
    calendarization: CalendarizationData | None = None
    days: list[ActiveProgramDay]


class ActiveProgramEnvelope(Schema):
    ok: Literal[True] = True
    data: ActiveProgramData
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
    action: Literal["completed", "skipped", "reset"]
    idempotency_key: str = Field(min_length=8, max_length=120)
    note: str = Field(default="", max_length=500)


class ReminderSettingsInput(Schema):
    timezone_name: str = Field(min_length=1, max_length=64)
    daily_notification_time: time
    daily_notifications_enabled: bool
    meal_notifications_enabled: bool


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


class OnboardingInput(Schema):
    birth_date: date
    sex: str
    height_cm: int = Field(ge=80, le=250)
    weight_kg: float = Field(ge=25, le=350)


class AccountDeletionInput(Schema):
    confirmation: str
    password: str = ""


class AccountDeletionData(Schema):
    receipt_id: str


class AccountDeletionEnvelope(Schema):
    ok: Literal[True] = True
    data: AccountDeletionData
    error: None = None


class RevokeSessionData(Schema):
    revoked: bool
    device_session_id: str


class RevokeSessionEnvelope(Schema):
    ok: Literal[True] = True
    data: RevokeSessionData
    error: None = None


class FoodItem(Schema):
    id: int
    name: str
    display_name: str
    protein: float
    carbs: float
    fat: float
    total_kcal: float
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


class AITurnInput(Schema):
    message: str = Field(min_length=1, max_length=2000)
    idempotency_key: str = Field(min_length=8, max_length=120)
    chat_id: int | None = None


class AIJobAcceptedData(Schema):
    job_id: str
    status: str
    retry_after_ms: int


class AIJobAcceptedEnvelope(Schema):
    ok: Literal[True] = True
    data: AIJobAcceptedData
    error: None = None


class AIJobResultData(Schema):
    job_id: str
    status: str
    retry_after_ms: int | None = None
    result: dict[str, Any] | None = None


class AIJobResultEnvelope(Schema):
    ok: Literal[True] = True
    data: AIJobResultData
    error: None = None
