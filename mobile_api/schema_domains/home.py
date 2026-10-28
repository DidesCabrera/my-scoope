from __future__ import annotations

from typing import Literal

from ninja import Schema

from mobile_api.schema_domains.calendarization import ActiveProgramData, WeightItem
from mobile_api.schema_domains.today import TodayData


class HomeLibraryCountsData(Schema):
    food: int
    meal: int
    daily_plan: int
    program: int


class HomeSummaryData(Schema):
    today: TodayData
    latest_weight: WeightItem | None = None
    library_counts: HomeLibraryCountsData
    pending_proposal_count: int
    version: str


class HomeData(HomeSummaryData):
    active_program: ActiveProgramData


class HomeSummaryEnvelope(Schema):
    ok: Literal[True] = True
    data: HomeSummaryData
    error: None = None


class HomeEnvelope(Schema):
    ok: Literal[True] = True
    data: HomeData
    error: None = None
