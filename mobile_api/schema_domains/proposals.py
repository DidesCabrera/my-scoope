from __future__ import annotations

from datetime import datetime
from typing import Literal

from ninja import Field, Schema

from mobile_api.schema_domains.proposal_entities import (
    ProposalDailyPlanData,
    ProposalDailyPlanMealData,
    ProposalFoodData,
    ProposalKpisData,
    ProposalMealData,
)


class MobileActionData(Schema):
    key: str
    label: str
    tone: Literal["default", "warning", "danger"] = "default"
    requires_confirmation: bool = True


class ProposalSummaryData(Schema):
    id: int
    title: str
    summary: str
    status: Literal["draft", "pending_review", "approved", "rejected", "cancelled", "applied"]
    status_label: str
    source: str
    attachment_kind: Literal["meal", "dailyplan", "program", "brief"]
    attachment_label: str
    attachment_name: str
    is_reviewable: bool
    created_at: datetime | None = None
    actions: list[MobileActionData] = Field(default_factory=list)


class ProposalListData(Schema):
    items: list[ProposalSummaryData]
    total: int
    offset: int
    limit: int
    pending_count: int


class ProposalListEnvelope(Schema):
    ok: Literal[True] = True
    data: ProposalListData
    error: None = None


class ProposalFactData(Schema):
    label: str
    value: str


class ProposalSubjectWarningData(Schema):
    requires_warning: bool
    source_label: str
    calculation_weight_label: str
    title: str
    message: str


class ProposalAppliedResultData(Schema):
    kind: Literal["meal", "dailyplan", "program"] | None = None
    object_id: int | None = None
    object_name: str = ""


class ProposalProgramDayData(Schema):
    week_number: int
    day_number: int
    dailyplan: ProposalDailyPlanData


class ProposalProgramData(Schema):
    name: str
    duration_weeks: int
    warnings: list[str] = Field(default_factory=list)
    days: list[ProposalProgramDayData]


class ProposalDetailData(ProposalSummaryData):
    dailyplan_id: int | None = None
    dailyplan_name: str = ""
    created_by_username: str
    reviewed_by_username: str | None = None
    intent: str | None = None
    entity_title: str
    target_facts: list[ProposalFactData] = Field(default_factory=list)
    current_facts: list[ProposalFactData] = Field(default_factory=list)
    validation_facts: list[ProposalFactData] = Field(default_factory=list)
    meal: ProposalMealData | None = None
    dailyplan: ProposalDailyPlanData | None = None
    program: ProposalProgramData | None = None
    subject_context_warning: ProposalSubjectWarningData
    applied_result: ProposalAppliedResultData | None = None
    applied_at: datetime | None = None


class ProposalDetailEnvelope(Schema):
    ok: Literal[True] = True
    data: ProposalDetailData
    error: None = None


class ProposalApplyInput(Schema):
    acknowledge_external_subject: bool = False
