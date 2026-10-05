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


class HomeData(Schema):
    today: TodayData
    active_program: ActiveProgramData
    latest_weight: WeightItem | None = None
    library_counts: HomeLibraryCountsData
    pending_proposal_count: int
    version: str


class HomeEnvelope(Schema):
    ok: Literal[True] = True
    data: HomeData
    error: None = None
