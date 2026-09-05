from __future__ import annotations

from typing import Any, Literal

from ninja import Field, Schema

from mobile_api.schema_domains.assistant import (  # noqa: F401 -- compatibility re-exports
    AIChatCardData,
    AIChatCardItemData,
    AIChatComparisonCardData,
    AIChatDetailData,
    AIChatDetailEnvelope,
    AIChatDraftCardData,
    AIChatGeneratedPlanCardData,
    AIChatListData,
    AIChatListEnvelope,
    AIChatMessageData,
    AIChatPreparedActionCardData,
    AIChatProposalCardData,
    AIChatSummaryData,
    AIJobAcceptedData,
    AIJobAcceptedEnvelope,
    AIJobResultData,
    AIJobResultEnvelope,
    AIPendingTurnData,
    AIPreparedActionResultData,
    AIPreparedActionResultEnvelope,
    AITurnInput,
    AITurnResultData,
    AssistantAvailabilityData,
)
from mobile_api.schema_domains.billing import (  # noqa: F401 -- compatibility re-exports
    AppleSubscriptionProductData,
    AppleTransactionInput,
    EntitlementsData,
    EntitlementsEnvelope,
    SubscriptionData,
    SubscriptionEnvelope,
    SubscriptionEvidenceData,
)
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
)
from mobile_api.schema_domains.composition_preview import (  # noqa: F401 -- compatibility re-exports
    PickerImpactData,
    PickerMetricData,
    PickerPreviewData,
    PickerPreviewEnvelope,
    PickerResultData,
    PickerSelectionData,
)
from mobile_api.schema_domains.identity import (  # noqa: F401 -- compatibility re-exports
    AccountDeletionData,
    AccountDeletionEnvelope,
    AccountDeletionInput,
    DisclosureAcceptanceInput,
    OnboardingInput,
    ProfileData,
    ProfileEnvelope,
    RevokeSessionData,
    RevokeSessionEnvelope,
    SessionData,
    SessionEnvelope,
)
from mobile_api.schema_domains.libraries import (  # noqa: F401 -- compatibility re-exports
    FoodCreateInput,
    FoodItem,
    FoodItemEnvelope,
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
