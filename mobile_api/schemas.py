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


class FoodItem(Schema):
    id: int
    name: str
    display_name: str
    protein: float
    carbs: float
    fat: float
    total_kcal: float
    protein_allocation: float
    carbs_allocation: float
    fat_allocation: float
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


class FoodItemEnvelope(Schema):
    ok: Literal[True] = True
    data: FoodItem
    error: None = None


class LibraryMacroData(Schema):
    grams: float
    allocation: float
    per_kilogram: float | None = None


class LibraryNutritionData(Schema):
    calories: float
    protein: LibraryMacroData
    carbs: LibraryMacroData
    fat: LibraryMacroData


class LibraryIndicatorData(Schema):
    icon: Literal["day", "food", "meal", "dailyPlan", "week"] | None = None
    label: str
    value: int | str


class LibraryCalorieDistributionData(Schema):
    protein: float
    carbs: float
    fat: float


class LibraryFoodPanelItemData(Schema):
    id: str
    relation_id: int | None = None
    name: str
    quantity: float
    quantity_unit: str
    calories: float
    calorie_share: float
    calorie_distribution: LibraryCalorieDistributionData
    protein_grams: float
    carbs_grams: float
    fat_grams: float
    protein_allocation: float
    carbs_allocation: float
    fat_allocation: float


class LibraryMealPanelItemData(Schema):
    id: str
    relation_id: int | None = None
    detail_id: int
    name: str
    time: str | None = None
    note: str = ""
    foods: list[LibraryFoodPanelItemData]
    calories: float
    calorie_share: float
    calorie_distribution: LibraryCalorieDistributionData
    protein_grams: float
    protein_per_kilogram: float | None = None
    carbs_grams: float
    fat_grams: float
    protein_allocation: float
    carbs_allocation: float
    fat_allocation: float


class LibraryWeekDayData(Schema):
    id: str
    program_day_id: int | None = None
    day_number: int
    day_label: str
    dailyplan_id: int | None = None
    plan_name: str | None = None
    nutrition: LibraryNutritionData | None = None
    meals: list[LibraryMealPanelItemData] = Field(default_factory=list)


class LibraryWeekPanelItemData(Schema):
    id: str
    week_number: int
    days: list[LibraryWeekDayData]
    filled_days_count: int
    meals_count: int
    foods_count: int
    average_calories: float
    foods: list[LibraryFoodPanelItemData] = Field(default_factory=list)
    calories: float
    calorie_share: float
    calorie_distribution: LibraryCalorieDistributionData
    protein_grams: float
    carbs_grams: float
    fat_grams: float
    protein_allocation: float
    carbs_allocation: float
    fat_allocation: float


class LibraryPanelData(Schema):
    kind: Literal["none", "foods", "meals", "weeks"]
    foods: list[LibraryFoodPanelItemData] = Field(default_factory=list)
    meals: list[LibraryMealPanelItemData] = Field(default_factory=list)
    weeks: list[LibraryWeekPanelItemData] = Field(default_factory=list)


class LibraryActionData(Schema):
    key: Literal["rename", "duplicate", "share", "delete"]
    label: str
    destructive: bool = False


class FoodCreateInput(Schema):
    name: str = Field(min_length=1, max_length=100)
    protein: float = Field(ge=0, le=100)
    carbs: float = Field(ge=0, le=100)
    fat: float = Field(ge=0, le=100)


class NamedLibraryCreateInput(Schema):
    name: str = Field(min_length=1, max_length=100)


class LibraryItemData(Schema):
    id: int
    entity: Literal["food", "meal", "dailyPlan", "program"]
    name: str
    subtitle: str
    nutrition: LibraryNutritionData
    indicators: list[LibraryIndicatorData]
    panel: LibraryPanelData
    creator: str
    created_at: datetime
    is_draft: bool = False
    can_calendarize: bool = False
    actions: list[LibraryActionData] = Field(default_factory=list)


class ComparisonOptionData(Schema):
    """Visual contract required to render an entity card in a comparison picker."""

    id: int
    entity: Literal["food", "meal", "dailyPlan"]
    name: str
    subtitle: str
    nutrition: LibraryNutritionData
    indicators: list[LibraryIndicatorData]
    panel: LibraryPanelData


class ComparisonOptionsData(Schema):
    items: list[ComparisonOptionData]
    total: int
    offset: int
    limit: int
    search: str | None = None


class ComparisonOptionsEnvelope(Schema):
    ok: Literal[True] = True
    data: ComparisonOptionsData
    error: None = None


class LibraryPageData(Schema):
    items: list[LibraryItemData]
    total: int
    offset: int
    limit: int
    search: str | None = None


class LibraryPageEnvelope(Schema):
    ok: Literal[True] = True
    data: LibraryPageData
    error: None = None


class LibraryItemEnvelope(Schema):
    ok: Literal[True] = True
    data: LibraryItemData
    error: None = None


class FoodPickerInput(Schema):
    food_id: int = Field(gt=0)
    quantity: float = Field(gt=0, le=100000)


class MealPickerInput(Schema):
    meal_id: int = Field(gt=0)
    dailyplan_meal_id: int | None = Field(default=None, gt=0)
    hour: time | None = None
    note: str = Field(default="", max_length=500)


class CompositionOrderInput(Schema):
    ordered_ids: list[int] = Field(min_length=1)


class MealFoodUpdateInput(Schema):
    quantity: float = Field(gt=0, le=100000)


class DailyPlanMealUpdateInput(Schema):
    hour: time | None = None
    note: str = Field(default="", max_length=500)


class CompositionMutationData(Schema):
    message: str
    target_id: int
    affected_id: int


class CompositionMutationEnvelope(Schema):
    ok: Literal[True] = True
    data: CompositionMutationData
    error: None = None


class DailyPlanPickerInput(Schema):
    dailyplan_id: int = Field(gt=0)
    week_number: int = Field(gt=0)
    day_numbers: list[int] = Field(min_length=1, max_length=7)
    confirm_replacements: bool = False


class PickerSelectionData(Schema):
    id: int
    entity: Literal["food", "meal", "dailyPlan", "week"]
    name: str
    nutrition: LibraryNutritionData | None = None
    quantity: float | None = None
    hour: str | None = None


class PickerMetricData(Schema):
    label: str
    before: float
    after: float


class PickerImpactData(Schema):
    label: str
    entity: Literal["meal", "dailyPlan", "week", "program"]
    before: LibraryNutritionData
    after: LibraryNutritionData
    metrics: list[PickerMetricData] = Field(default_factory=list)


class PickerPreviewData(Schema):
    selection: PickerSelectionData
    impacts: list[PickerImpactData]
    replacements: list[str] = Field(default_factory=list)
    confirmation_required: bool = False


class PickerPreviewEnvelope(Schema):
    ok: Literal[True] = True
    data: PickerPreviewData
    error: None = None


class PickerCommitData(Schema):
    message: str
    target_id: int
    created_id: int


class PickerCommitEnvelope(Schema):
    ok: Literal[True] = True
    data: PickerCommitData
    error: None = None


class LibraryActionInput(Schema):
    action: Literal["rename", "duplicate", "share", "delete"]
    name: str = Field(default="", max_length=100)
    recipient_email: str = Field(default="", max_length=254)
    subject: str = Field(default="", max_length=160)
    message: str = Field(default="", max_length=2000)


class LibraryActionResultData(Schema):
    action: Literal["rename", "duplicate", "share", "delete"]
    item_id: int
    message: str


class LibraryActionResultEnvelope(Schema):
    ok: Literal[True] = True
    data: LibraryActionResultData
    error: None = None


class LibraryOrderInput(Schema):
    ordered_ids: list[int] = Field(min_length=1)


class LibraryBulkDeleteInput(Schema):
    item_ids: list[int] = Field(min_length=1)


class LibraryListActionResultData(Schema):
    affected_ids: list[int]
    skipped_ids: list[int] = Field(default_factory=list)
    message: str


class LibraryListActionResultEnvelope(Schema):
    ok: Literal[True] = True
    data: LibraryListActionResultData
    error: None = None


class FoodLabelCaptureInput(Schema):
    name: str = Field(min_length=1, max_length=100)
    protein_g: float = Field(ge=0, le=100)
    carbs_g: float = Field(ge=0, le=100)
    fat_g: float = Field(ge=0, le=100)
    saturated_fat_g: float | None = Field(default=None, ge=0, le=100)
    sugar_g: float | None = Field(default=None, ge=0, le=100)
    fiber_g: float | None = Field(default=None, ge=0, le=100)
    sodium_mg: float | None = Field(default=None, ge=0, le=100_000)
    serving_size_g: float | None = Field(default=None, gt=0, le=10_000)
    declared_energy_kcal_per_100g: float | None = Field(default=None, ge=0, le=10_000)
    detected_basis: Literal["per_100g", "per_serving", "manual"]
    ocr_engine: str = Field(min_length=1, max_length=80)
    ocr_engine_version: str = Field(default="", max_length=40)
    field_confidence: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    idempotency_key: str = Field(min_length=8, max_length=120)


class FoodLabelCaptureData(Schema):
    id: int
    name: str
    protein_g: float
    carbs_g: float
    fat_g: float
    saturated_fat_g: float | None = None
    sugar_g: float | None = None
    fiber_g: float | None = None
    sodium_mg: float | None = None
    total_kcal: float
    is_user_food: bool
    is_verified: bool
    capture_receipt_id: int
    detected_basis: str
    serving_size_g: float | None = None
    ocr_engine: str
    created_at: datetime


class FoodLabelCaptureEnvelope(Schema):
    ok: Literal[True] = True
    data: FoodLabelCaptureData
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
