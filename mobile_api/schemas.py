from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Literal

from ninja import Field, Schema

from mobile_api.schema_domains.calendarization import (  # noqa: F401 -- compatibility re-exports
    ActiveProgramData,
    ActiveProgramDay,
    ActiveProgramEnvelope,
    ActiveProgramIndicatorData,
    AdherenceData,
    ApplePushRegistrationData,
    ApplePushRegistrationEnvelope,
    ApplePushRegistrationInput,
    CalendarizationActivationData,
    CalendarizationActivationEnvelope,
    CalendarizationActivationInput,
    CalendarizationData,
    CalendarizationHistoryData,
    CalendarizationHistoryEnvelope,
    CalendarizationHistoryItem,
    CalendarizationReviewData,
    CalendarizationReviewEnvelope,
    CalendarizationReviewInput,
    CalendarizationReviewListData,
    CalendarizationReviewListEnvelope,
    CalendarizationRevisionData,
    CalendarizedDayDetailData,
    CalendarizedDayDetailEnvelope,
    MealCheckInInput,
    MealExecutionData,
    MeasurementSummaryData,
    ReminderEventData,
    ReminderSettingsData,
    ReminderSettingsEnvelope,
    ReminderSettingsInput,
    RevisionDayComparisonData,
    RevisionDecisionInput,
    RevisionEnvelope,
    RevisionListData,
    RevisionListEnvelope,
    TodayData,
    TodayEnvelope,
    WeightCreateInput,
    WeightEnvelope,
    WeightItem,
    WeightListData,
    WeightListEnvelope,
)
from mobile_api.schema_domains.comparisons import (  # noqa: F401 -- compatibility re-exports
    ComparisonKindData,
    ComparisonMetadataData,
    ComparisonMetadataEnvelope,
    ComparisonMetricBarData,
    ComparisonMetricData,
    ComparisonMetricValuesData,
    ComparisonOptionData,
    ComparisonOptionsData,
    ComparisonOptionsEnvelope,
    ComparisonRequestInput,
    ComparisonResultData,
    ComparisonResultEnvelope,
    ComparisonResultItemData,
    ComparisonSelectionInput,
    SavedComparisonDetailData,
    SavedComparisonDetailEnvelope,
    SavedComparisonListData,
    SavedComparisonListEnvelope,
    SavedComparisonSummaryData,
)
from mobile_api.schema_domains.composition import (  # noqa: F401 -- compatibility re-exports
    CompositionMutationData,
    CompositionMutationEnvelope,
    CompositionOrderInput,
    DailyPlanMealUpdateInput,
    DailyPlanPickerInput,
    FoodPickerInput,
    MealFoodUpdateInput,
    MealPickerInput,
    PickerCommitData,
    PickerCommitEnvelope,
    PickerImpactData,
    PickerMetricData,
    PickerPreviewData,
    PickerPreviewEnvelope,
    PickerSelectionData,
)
from mobile_api.schema_domains.libraries import (  # noqa: F401 -- compatibility re-exports
    FoodCreateInput,
    FoodItem,
    FoodItemEnvelope,
    FoodLabelCaptureData,
    FoodLabelCaptureEnvelope,
    FoodLabelCaptureInput,
    FoodPageData,
    FoodPageEnvelope,
    LibraryActionData,
    LibraryActionInput,
    LibraryActionResultData,
    LibraryActionResultEnvelope,
    LibraryBulkDeleteInput,
    LibraryCalorieDistributionData,
    LibraryFoodPanelItemData,
    LibraryIndicatorData,
    LibraryItemData,
    LibraryItemEnvelope,
    LibraryListActionResultData,
    LibraryListActionResultEnvelope,
    LibraryMacroData,
    LibraryMealPanelItemData,
    LibraryNutritionData,
    LibraryOrderInput,
    LibraryPageData,
    LibraryPageEnvelope,
    LibraryPanelData,
    LibraryWeekDayData,
    LibraryWeekPanelItemData,
    NamedLibraryCreateInput,
)
from mobile_api.schema_domains.proposals import (  # noqa: F401 -- compatibility re-exports
    MobileActionData,
    ProposalAppliedResultData,
    ProposalApplyInput,
    ProposalDailyPlanData,
    ProposalDailyPlanMealData,
    ProposalDetailData,
    ProposalDetailEnvelope,
    ProposalFactData,
    ProposalFoodData,
    ProposalKpisData,
    ProposalListData,
    ProposalListEnvelope,
    ProposalMealData,
    ProposalSubjectWarningData,
    ProposalSummaryData,
)


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
    review_disclosure_required: bool
    review_disclosure_version: str


class ProfileEnvelope(Schema):
    ok: Literal[True] = True
    data: ProfileData
    error: None = None


class DisclosureAcceptanceInput(Schema):
    accepted: Literal[True]


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


class AppleSubscriptionProductData(Schema):
    product_id: str
    plan_name: str
    interval: str


class SubscriptionEvidenceData(Schema):
    provider: str
    status: str
    period_end: datetime | None = None


class SubscriptionData(Schema):
    eligible: bool
    purchases_enabled: bool
    app_account_token: str
    plan_name: str
    status: str
    products: list[AppleSubscriptionProductData]
    evidence: list[SubscriptionEvidenceData]
    duplicate_active_providers: bool


class SubscriptionEnvelope(Schema):
    ok: Literal[True] = True
    data: SubscriptionData
    error: None = None


class AppleTransactionInput(Schema):
    signed_transaction: str = Field(min_length=20, max_length=20000)


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
