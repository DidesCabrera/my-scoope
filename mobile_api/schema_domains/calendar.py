from datetime import date
from typing import Any, Literal

from ninja import Field, Schema


class CalendarDayData(Schema):
    id: int | None = None
    calendar_date: date
    has_plan: bool
    plan_name: str = ""
    source_kind: str | None = None
    source_program_name: str | None = None
    has_execution: bool = False


class CalendarOverviewData(Schema):
    local_date: date
    start_date: date
    end_date: date
    days: list[CalendarDayData]
    future_plans_count: int
    last_scheduled_date: date | None = None


class CalendarOverviewEnvelope(Schema):
    ok: Literal[True] = True
    data: CalendarOverviewData
    error: None = None


class CalendarDayDetailData(CalendarDayData):
    plan_snapshot: dict[str, Any] | None = None
    meal_execution: list[dict[str, Any]] = Field(default_factory=list)


class CalendarDayDetailEnvelope(Schema):
    ok: Literal[True] = True
    data: CalendarDayDetailData
    error: None = None


class CalendarDayHistoryItem(Schema):
    id: int
    calendar_date: date
    plan_name: str
    source_kind: str
    source_program_name: str | None = None
    assignment_state: str
    created_at: str
    state_changed_at: str | None = None
    change_reason: str = ""
    superseded_by_id: int | None = None
    execution_events: int = 0


class CalendarDayHistoryData(Schema):
    calendar_date: date
    items: list[CalendarDayHistoryItem]


class CalendarDayHistoryEnvelope(Schema):
    ok: Literal[True] = True
    data: CalendarDayHistoryData
    error: None = None


class CalendarAssignmentInput(Schema):
    dailyplan_id: int = Field(gt=0)
    assignment_key: str = Field(min_length=8, max_length=120)
    replace_existing: bool = False


class CalendarMoveInput(Schema):
    target_date: date
    assignment_key: str = Field(min_length=8, max_length=120)
    replace_existing: bool = False


class CalendarDraftInput(Schema):
    assignment_key: str = Field(min_length=8, max_length=120)


class CalendarProgressData(Schema):
    period_id: int | None = None
    period_start: date
    period_end: date
    days_with_plan: int
    scheduled_meals: int
    elapsed_meals: int
    completed_meals: int
    skipped_meals: int
    unrecorded_meals: int
    adherence_percent: int


class CalendarProgressEnvelope(Schema):
    ok: Literal[True] = True
    data: CalendarProgressData
    error: None = None
