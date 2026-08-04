"""Executable ownership map for domain models.

The domain remains a single Django app and ``notas/domain/models.py`` remains the
public compatibility import for now.  This module makes the model boundaries
explicit before physically splitting the file into smaller modules.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainModelBoundary:
    """Ownership declaration for a group of Django model classes."""

    slug: str
    label: str
    models: tuple[str, ...]
    responsibility: str


@dataclass(frozen=True)
class DomainModelDependencyPolicy:
    """Allowed model-reference direction between domain model boundaries."""

    source_slug: str
    allowed_dependency_slugs: tuple[str, ...]
    rationale: str


DOMAIN_MODEL_BOUNDARIES: tuple[DomainModelBoundary, ...] = (
    DomainModelBoundary(
        slug="identity",
        label="Identity & User State",
        models=("Plan", "Profile", "Subscription", "NutritionistMemberRelationship", "WeightLog"),
        responsibility=(
            "Nutrition profile and personal state. Subscription is the legacy "
            "name behind the NutritionistMemberRelationship compatibility façade."
        ),
    ),
    DomainModelBoundary(
        slug="auth_integration",
        label="Auth Integration",
        models=("MCPUserToken", "OAuthClient", "OAuthAuthorizationCode"),
        responsibility="Tokens and OAuth authorization state used by external integrations.",
    ),
    DomainModelBoundary(
        slug="food_catalog",
        label="Operational Food Snapshot",
        models=(
            "Food",
            "FoodSourceMetadata",
            "FoodPortion",
            "FoodAlias",
            "FoodLocalizedName",
            "FoodImportBatch",
        ),
        responsibility=(
            "Operational food snapshots, portions, aliases, localized names, "
            "source metadata and imports currently owned by notas.Food."
        ),
    ),
    DomainModelBoundary(
        slug="meals",
        label="Meals",
        models=("Meal", "MealFood", "MealAccess"),
        responsibility="Reusable meals, meal-food composition and meal-specific access metadata.",
    ),
    DomainModelBoundary(
        slug="dailyplans",
        label="Daily Plans",
        models=("DailyPlan", "DailyPlanMeal"),
        responsibility="Daily plans and the meals attached to each plan.",
    ),
    DomainModelBoundary(
        slug="programs",
        label="Programs",
        models=("Program", "ProgramDay"),
        responsibility="Weekly programs and their copied daily-plan days.",
    ),
    DomainModelBoundary(
        slug="calendarization",
        label="Calendarization",
        models=("ProgramCalendarization", "CalendarizedDay"),
        responsibility="Dated executions and immutable daily snapshots derived from weekly programs.",
    ),
    DomainModelBoundary(
        slug="notification_delivery",
        label="Notification Delivery",
        models=("WebPushSubscription", "ScheduledNotificationEvent", "NotificationDelivery"),
        responsibility="Web Push subscriptions, logical scheduled events and per-device delivery attempts.",
    ),
    DomainModelBoundary(
        slug="proposals",
        label="AI Proposals",
        models=("AiNutritionChat", "NutritionProposal", "NutritionProposalAuditEvent"),
        responsibility="AI chat state, reviewable nutrition proposals and proposal audit history.",
    ),
    DomainModelBoundary(
        slug="sharing",
        label="Sharing",
        models=(
            "DailyPlanShare",
            "ProgramShare",
            "MealShare",
            "FoodShare",
            "DailyPlanMealShare",
        ),
        responsibility="Inbox/share records for entities sent between users.",
    ),
    DomainModelBoundary(
        slug="comparisons",
        label="Comparisons",
        models=("SavedComparison",),
        responsibility="Saved comparison payloads and snapshots.",
    ),
)


DOMAIN_MODEL_DEPENDENCY_POLICIES: tuple[DomainModelDependencyPolicy, ...] = (
    DomainModelDependencyPolicy(
        source_slug="identity",
        allowed_dependency_slugs=(),
        rationale="Identity/user-state models are foundational and do not depend on feature models.",
    ),
    DomainModelDependencyPolicy(
        source_slug="auth_integration",
        allowed_dependency_slugs=(),
        rationale="External auth state stays isolated from feature models.",
    ),
    DomainModelDependencyPolicy(
        source_slug="food_catalog",
        allowed_dependency_slugs=(),
        rationale="Operational foods are foundational for nutrition-management entities.",
    ),
    DomainModelDependencyPolicy(
        source_slug="meals",
        allowed_dependency_slugs=("food_catalog", "dailyplans"),
        rationale="Meals compose foods and may expose legacy links to daily plans.",
    ),
    DomainModelDependencyPolicy(
        source_slug="dailyplans",
        allowed_dependency_slugs=("meals",),
        rationale="Daily plans attach meals through DailyPlanMeal.",
    ),
    DomainModelDependencyPolicy(
        source_slug="programs",
        allowed_dependency_slugs=("dailyplans",),
        rationale="Programs store copied daily plans per program day.",
    ),
    DomainModelDependencyPolicy(
        source_slug="calendarization",
        allowed_dependency_slugs=("programs",),
        rationale="Calendarizations retain an optional trace to the source Program and own dated snapshots.",
    ),
    DomainModelDependencyPolicy(
        source_slug="notification_delivery",
        allowed_dependency_slugs=("calendarization",),
        rationale="Notification events are scheduled for calendarized days and deliveries remain device-specific.",
    ),
    DomainModelDependencyPolicy(
        source_slug="proposals",
        allowed_dependency_slugs=("dailyplans",),
        rationale="Nutrition proposals may reference the created/applied DailyPlan snapshot.",
    ),
    DomainModelDependencyPolicy(
        source_slug="sharing",
        allowed_dependency_slugs=("food_catalog", "meals", "dailyplans", "programs"),
        rationale="Share records point at the entity being shared and do not own that entity.",
    ),
    DomainModelDependencyPolicy(
        source_slug="comparisons",
        allowed_dependency_slugs=(),
        rationale="Saved comparisons persist self-contained payloads rather than model references.",
    ),
)




# Physical modules already split out of the legacy compatibility module.
# Boundaries omitted from this mapping still live directly in ``notas.domain.models``.
DOMAIN_MODEL_MODULE_BY_BOUNDARY_SLUG: dict[str, str] = {
    "identity": "notas.domain.model_modules.identity",
    "auth_integration": "notas.domain.model_modules.auth_integration",
    "sharing": "notas.domain.model_modules.sharing",
    "comparisons": "notas.domain.model_modules.comparisons",
    "proposals": "notas.domain.model_modules.proposals",
    "calendarization": "notas.domain.model_modules.calendarization",
    "notification_delivery": "notas.domain.model_modules.notification_delivery",
    "food_catalog": "notas.domain.model_modules.food",
    "meals": "notas.domain.model_modules.meals",
    "dailyplans": "notas.domain.model_modules.dailyplans",
    "programs": "notas.domain.model_modules.programs",
}

DOMAIN_MODEL_BOUNDARY_BY_MODEL: dict[str, DomainModelBoundary] = {
    model_name: boundary
    for boundary in DOMAIN_MODEL_BOUNDARIES
    for model_name in boundary.models
}


DOMAIN_MODEL_POLICY_BY_SLUG: dict[str, DomainModelDependencyPolicy] = {
    policy.source_slug: policy
    for policy in DOMAIN_MODEL_DEPENDENCY_POLICIES
}


def boundary_for_model(model_name: str) -> DomainModelBoundary | None:
    """Return the boundary that owns a Django model class name."""

    return DOMAIN_MODEL_BOUNDARY_BY_MODEL.get(model_name)


def allowed_dependency_slugs_for_model_boundary(source_slug: str) -> frozenset[str]:
    """Return allowed dependency boundary slugs for a domain-model boundary."""

    policy = DOMAIN_MODEL_POLICY_BY_SLUG.get(source_slug)
    if policy is None:
        return frozenset()

    return frozenset(policy.allowed_dependency_slugs)
