from __future__ import annotations

from datetime import datetime
from typing import Literal

from ninja import Field, Schema

from mobile_api.schema_domains.proposals import ProposalSummaryData


class AIChatCardItemData(Schema):
    key: str
    label: str
    value: str
    is_pending: bool = False


class AIChatDraftCardData(Schema):
    type: Literal["profile_draft", "preference_draft", "proposal_preferences"]
    title: str
    subtitle: str = ""
    items: list[AIChatCardItemData] = Field(default_factory=list)
    status: str = ""
    can_commit: bool = False


class AIChatProposalCardData(Schema):
    type: Literal["proposal_review"]
    proposal_id: int
    title: str
    summary: str = ""
    status: str = ""
    proposal: ProposalSummaryData | None = None


class AIChatComparisonCardData(Schema):
    type: Literal["saved_comparison"]
    comparison_id: int
    kind: Literal["foods", "meals", "dailyplans"]
    title: str


class AIChatLibraryCardData(Schema):
    type: Literal["library_item"]
    item_id: int
    entity: Literal["food", "meal", "dailyPlan", "program"]
    resource: Literal["foods", "meals", "dailyplans", "programs"]
    title: str


class AIChatPreparedActionCardData(Schema):
    type: Literal["prepared_action"]
    action_id: str
    title: str
    summary: str = ""
    status: Literal["prepared", "committed", "cancelled", "expired", "failed"]
    destructive: bool = False
    risk_level: Literal["low", "medium", "high"] = "medium"
    operation_count: int = 1
    operations: list[str] = Field(default_factory=list)
    expires_at: datetime


class AIChatGeneratedPlanCardData(Schema):
    type: Literal["generated_plan"]
    proposal_id: int | None = None
    title: str
    summary: str = ""
    is_current: bool = False
    items: list[AIChatCardItemData] = Field(default_factory=list)
    proposal: ProposalSummaryData | None = None


AIChatCardData = (
    AIChatDraftCardData
    | AIChatProposalCardData
    | AIChatComparisonCardData
    | AIChatLibraryCardData
    | AIChatPreparedActionCardData
    | AIChatGeneratedPlanCardData
)
