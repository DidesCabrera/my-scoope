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
    attachment_kind: Literal["meal", "dailyplan", "brief"]
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


class ProposalKpisData(Schema):
    total_kcal: float | None = None
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None
    ppk: float | None = None


class ProposalFoodData(Schema):
    food_id: int | None = None
    food_name: str
    quantity: float | None = None
    unit: str = "g"


class ProposalMealData(Schema):
    name: str
    foods: list[ProposalFoodData] = Field(default_factory=list)
    kpis: ProposalKpisData | None = None


class ProposalDailyPlanMealData(Schema):
    hour: str | None = None
    note: str = ""
    meal: ProposalMealData


class ProposalDailyPlanData(Schema):
    name: str
    meals: list[ProposalDailyPlanMealData] = Field(default_factory=list)
    kpis: ProposalKpisData | None = None


class ProposalSubjectWarningData(Schema):
    requires_warning: bool
    source_label: str
    calculation_weight_label: str
    title: str
    message: str


class ProposalAppliedResultData(Schema):
    kind: Literal["meal", "dailyplan"] | None = None
    object_id: int | None = None
    object_name: str = ""


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
    subject_context_warning: ProposalSubjectWarningData
    applied_result: ProposalAppliedResultData | None = None
    applied_at: datetime | None = None


class ProposalDetailEnvelope(Schema):
    ok: Literal[True] = True
    data: ProposalDetailData
    error: None = None


class ProposalApplyInput(Schema):
    acknowledge_external_subject: bool = False


class ComparisonKindData(Schema):
    key: Literal["foods", "meals", "dailyplans"]
    label: str
    entity_label: str
    uses_quantity: bool
    quantity_unit: str | None = None
    includes_ppk: bool


class ComparisonMetadataData(Schema):
    kinds: list[ComparisonKindData]


class ComparisonMetadataEnvelope(Schema):
    ok: Literal[True] = True
    data: ComparisonMetadataData
    error: None = None


class ComparisonOptionData(Schema):
    id: int
    name: str


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


class ComparisonSelectionInput(Schema):
    id: int = Field(gt=0)
    quantity: float | None = None


class ComparisonRequestInput(Schema):
    kind: Literal["foods", "meals", "dailyplans"]
    selections: list[ComparisonSelectionInput] = Field(min_length=2)


class ComparisonMetricValuesData(Schema):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    protein_per_kilogram: float | None = None


class ComparisonMetricBarData(Schema):
    position: int
    id: int
    label: str
    quantity: float | None = None
    value: float
    formatted_value: str
    relative_percentage: float


class ComparisonMetricData(Schema):
    key: Literal["total_kcal", "ppk", "protein", "carbs", "fat", "alloc_protein", "alloc_carbs", "alloc_fat"]
    label: str
    unit: str
    bars: list[ComparisonMetricBarData]


class ComparisonResultItemData(Schema):
    position: int
    id: int
    name: str
    quantity: float | None = None
    values: ComparisonMetricValuesData


class ComparisonResultData(Schema):
    kind: Literal["foods", "meals", "dailyplans"]
    kind_label: str
    historical_snapshot: bool = False
    saved_comparison_id: int | None = None
    saved_comparison_name: str = ""
    metrics: list[ComparisonMetricData]
    items: list[ComparisonResultItemData]


class ComparisonResultEnvelope(Schema):
    ok: Literal[True] = True
    data: ComparisonResultData
    error: None = None


class SavedComparisonSummaryData(Schema):
    id: int
    name: str
    kind: Literal["foods", "meals", "dailyplans"]
    kind_label: str
    item_count: int
    updated_at: datetime


class SavedComparisonListData(Schema):
    items: list[SavedComparisonSummaryData]
    total: int
    offset: int
    limit: int


class SavedComparisonListEnvelope(Schema):
    ok: Literal[True] = True
    data: SavedComparisonListData
    error: None = None


class SavedComparisonDetailData(ComparisonResultData):
    editable_selections: list[ComparisonSelectionInput]
    updated_at: datetime


class SavedComparisonDetailEnvelope(Schema):
    ok: Literal[True] = True
    data: SavedComparisonDetailData
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
    detail_id: int
    name: str
    time: str | None = None
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
    can_calendarize: bool = False
    actions: list[LibraryActionData] = Field(default_factory=list)


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
