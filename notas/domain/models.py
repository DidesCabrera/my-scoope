"""Public compatibility façade for models owned by the ``notas`` Django app.

Concrete models live in responsibility-focused modules. Existing imports from
``notas.domain.models`` remain stable while new code may import the owning module
when that makes the dependency boundary clearer.
"""

from notas.domain.model_modules.auth_integration import (
    MCPUserToken,
    OAuthAuthorizationCode,
    OAuthClient,
    OAuthDeviceSession,
    OAuthRefreshToken,
)
from notas.domain.model_modules.calendarization import (
    CalendarizationMeasurementContext,
    CalendarizationReview,
    CalendarizationRevision,
    CalendarizedDay,
    CalendarizedMealExecution,
    ProgramCalendarization,
)
from notas.domain.model_modules.comparisons import SavedComparison
from notas.domain.model_modules.dailyplans import DailyPlan, DailyPlanMeal
from notas.domain.model_modules.food import (
    Food,
    FoodAlias,
    FoodImportBatch,
    FoodLabelCaptureReceipt,
    FoodLocalizedName,
    FoodPortion,
    FoodSourceMetadata,
)
from notas.domain.model_modules.identity import (
    NutritionistMemberRelationship,
    Plan,
    Profile,
    Subscription,
    WeightLog,
)
from notas.domain.model_modules.meals import Meal, MealAccess, MealFood
from notas.domain.model_modules.notification_delivery import (
    ApplePushSubscription,
    NotificationDelivery,
    ScheduledNotificationEvent,
    WebPushSubscription,
)
from notas.domain.model_modules.programs import Program, ProgramDay
from notas.domain.model_modules.proposals import (
    AiNutritionChat,
    NutritionProposal,
    NutritionProposalAuditEvent,
)
from notas.domain.model_modules.sharing import (
    DailyPlanMealShare,
    DailyPlanShare,
    FoodShare,
    MealShare,
    ProgramShare,
)

__all__ = [
    "AiNutritionChat",
    "ApplePushSubscription",
    "CalendarizedDay",
    "CalendarizedMealExecution",
    "CalendarizationMeasurementContext",
    "CalendarizationReview",
    "CalendarizationRevision",
    "DailyPlan",
    "DailyPlanMeal",
    "DailyPlanMealShare",
    "DailyPlanShare",
    "Food",
    "FoodAlias",
    "FoodImportBatch",
    "FoodLabelCaptureReceipt",
    "FoodLocalizedName",
    "FoodPortion",
    "FoodShare",
    "FoodSourceMetadata",
    "MCPUserToken",
    "Meal",
    "MealAccess",
    "MealFood",
    "MealShare",
    "NotificationDelivery",
    "NutritionProposal",
    "NutritionProposalAuditEvent",
    "NutritionistMemberRelationship",
    "OAuthAuthorizationCode",
    "OAuthClient",
    "OAuthDeviceSession",
    "OAuthRefreshToken",
    "Plan",
    "Profile",
    "Program",
    "ProgramCalendarization",
    "ProgramDay",
    "ProgramShare",
    "SavedComparison",
    "ScheduledNotificationEvent",
    "Subscription",
    "WebPushSubscription",
    "WeightLog",
]
