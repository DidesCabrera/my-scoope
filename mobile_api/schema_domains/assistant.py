from __future__ import annotations

from datetime import datetime
from typing import Literal

from ninja import Field, Schema


class AITurnInput(Schema):
    message: str = Field(min_length=1, max_length=2000)
    idempotency_key: str = Field(min_length=8, max_length=120)
    chat_id: int | None = None
    comparison_id: int | None = Field(default=None, gt=0)


class AIJobAcceptedData(Schema):
    job_id: str
    status: str
    retry_after_ms: int


class AIJobAcceptedEnvelope(Schema):
    ok: Literal[True] = True
    data: AIJobAcceptedData
    error: None = None


class AssistantAvailabilityData(Schema):
    is_available: bool
    label: str
    queue_available: bool
    available_credits: int
    monthly_credit_limit: int
    daily_credit_limit: int
    max_message_chars: int


class AIPendingTurnData(Schema):
    job_id: str
    status: Literal["queued", "running", "retrying"]
    retry_after_ms: int


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


class AIChatProposalCardData(Schema):
    type: Literal["proposal_review"]
    proposal_id: int
    title: str
    summary: str = ""
    status: str = ""


class AIChatComparisonCardData(Schema):
    type: Literal["saved_comparison"]
    comparison_id: int
    kind: Literal["foods", "meals", "dailyplans"]
    title: str


class AIChatPreparedActionCardData(Schema):
    type: Literal["prepared_action"]
    action_id: str
    title: str
    summary: str = ""
    status: Literal["prepared", "committed", "cancelled", "expired", "failed"]
    destructive: bool = False
    expires_at: datetime


class AIChatGeneratedPlanCardData(Schema):
    type: Literal["generated_plan"]
    proposal_id: int | None = None
    title: str
    summary: str = ""
    is_current: bool = False
    items: list[AIChatCardItemData] = Field(default_factory=list)


AIChatCardData = (
    AIChatDraftCardData
    | AIChatProposalCardData
    | AIChatComparisonCardData
    | AIChatPreparedActionCardData
    | AIChatGeneratedPlanCardData
)


class AIChatMessageData(Schema):
    id: str
    role: Literal["user", "assistant"]
    text: str
    created_at: datetime | None = None
    has_structured_content: bool = False
    cards: list[AIChatCardData] = Field(default_factory=list)


class AIPreparedActionResultData(Schema):
    action_id: str
    status: Literal["committed", "cancelled"]
    refresh_chat: bool = True


class AIPreparedActionResultEnvelope(Schema):
    ok: Literal[True] = True
    data: AIPreparedActionResultData
    error: None = None


class AIChatSummaryData(Schema):
    id: int
    title: str
    status: str
    status_label: str
    last_message_preview: str
    message_count: int
    proposal_id: int | None = None
    updated_at: datetime


class AIChatListData(Schema):
    items: list[AIChatSummaryData]
    total: int
    offset: int
    limit: int
    availability: AssistantAvailabilityData
    pending_new_turn: AIPendingTurnData | None = None


class AIChatListEnvelope(Schema):
    ok: Literal[True] = True
    data: AIChatListData
    error: None = None


class AIChatDetailData(AIChatSummaryData):
    messages: list[AIChatMessageData]
    availability: AssistantAvailabilityData
    pending_turn: AIPendingTurnData | None = None


class AIChatDetailEnvelope(Schema):
    ok: Literal[True] = True
    data: AIChatDetailData
    error: None = None


class AITurnResultData(Schema):
    chat_id: int
    conversation_updated: Literal[True] = True
    has_iteration_warning: bool = False


class AIJobResultData(Schema):
    job_id: str
    status: str
    retry_after_ms: int | None = None
    result: AITurnResultData | None = None


class AIJobResultEnvelope(Schema):
    ok: Literal[True] = True
    data: AIJobResultData
    error: None = None
