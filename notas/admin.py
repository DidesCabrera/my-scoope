from django.contrib import admin

from .admin_food_actions import (
    mark_foods_as_active,
    mark_foods_as_core,
    mark_foods_as_extended,
    mark_foods_as_hidden,
    mark_foods_as_inactive,
    mark_foods_as_rejected,
    mark_foods_as_unverified,
    mark_foods_as_verified,
)
from .domain.models import (
    CalendarizedDay,
    DailyPlan,
    DailyPlanMeal,
    Food,
    FoodAlias,
    FoodImportBatch,
    FoodLocalizedName,
    FoodPortion,
    FoodSourceMetadata,
    Meal,
    MealFood,
    NotificationDelivery,
    NutritionistMemberRelationship,
    NutritionProposal,
    NutritionProposalAuditEvent,
    Plan,
    Profile,
    Program,
    ProgramCalendarization,
    ProgramDay,
    ScheduledNotificationEvent,
    WebPushSubscription,
    WeightLog,
)

# =============================================================================
# Account / subscription
# =============================================================================

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role",
        "is_verified",
        "sex",
        "height_cm",
        "onboarding_version",
        "onboarding_completed_at",
        "timezone_name",
        "created_at",
    )

    list_filter = (
        "role",
        "is_verified",
        "sex",
        "onboarding_version",
        "onboarding_completed_at",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "created_at",
    )

    fieldsets = (
        (None, {
            "fields": (
                "user",
                "role",
                "is_verified",
            )
        }),
        ("Nutrition profile", {
            "fields": (
                "birth_date",
                "sex",
                "height_cm",
                "onboarding_completed_at",
                "onboarding_version",
                "timezone_name",
            )
        }),
        ("System", {
            "fields": ("created_at",)
        }),
    )


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "role",
        "can_create_meal",
        "can_create_dailyplan",
        "can_create_program",
        "can_publish",
        "can_fork",
        "can_copy",
        "created_at",
    )

    list_filter = (
        "role",
        "can_create_meal",
        "can_create_dailyplan",
        "can_create_program",
        "can_publish",
        "can_fork",
        "can_copy",
    )

    search_fields = (
        "name",
    )

    readonly_fields = (
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NutritionistMemberRelationship)
class NutritionistMemberRelationshipAdmin(admin.ModelAdmin):
    list_display = (
        "nutritionist",
        "member",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "created_at",
    )

    search_fields = (
        "nutritionist__username",
        "nutritionist__email",
        "member__username",
        "member__email",
    )

    readonly_fields = (
        "created_at",
    )


# =============================================================================
# Foods / nutrition database enrichment
# =============================================================================

class FoodSourceMetadataInline(admin.StackedInline):
    model = FoodSourceMetadata
    extra = 0
    max_num = 1
    can_delete = True

    fields = (
        "source",
        "source_food_id",
        "source_dataset",
        "source_version",
        "source_url",
        "license_name",
        "attribution",
        "raw_payload_hash",
        "normalized_payload_hash",
        "imported_at",
        "last_synced_at",
    )

    readonly_fields = (
        "imported_at",
    )


class FoodPortionInline(admin.TabularInline):
    model = FoodPortion
    extra = 0

    fields = (
        "label",
        "grams",
        "source",
        "is_default",
    )


class FoodAliasInline(admin.TabularInline):
    model = FoodAlias
    extra = 0

    fields = (
        "name",
        "normalized_name",
        "language",
        "country",
    )


class FoodLocalizedNameInline(admin.TabularInline):
    model = FoodLocalizedName
    extra = 0

    fields = (
        "name",
        "normalized_name",
        "language",
        "country",
        "is_primary",
    )


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_by",
        "category",
        "food_group",
        "food_subgroup",
        "preparation_state",
        "solver_enabled",
        "protein",
        "carbs",
        "fat",
        "total_kcal_display",
        "is_global",
        "is_verified",
        "is_active",
        "visibility",
        "data_quality_score",
        "catalog_sync_status",
        "catalog_food_id",
        "created_at",
    )

    list_filter = (
        "is_global",
        "is_verified",
        "is_active",
        "visibility",
        "catalog_sync_status",
        "solver_enabled",
        "preparation_state",
        "food_group",
        "food_subgroup",
        "created_at",
    )

    search_fields = (
        "name",
        "canonical_name",
        "created_by__username",
        "created_by__email",
        "aliases__name",
        "aliases__normalized_name",
        "source_metadata__source_food_id",
        "=catalog_food_id",
        "=catalog_food_ref",
    )

    readonly_fields = (
        "created_at",
        "total_kcal_display",
        "catalog_snapshot_created_at",
    )

    fieldsets = (
        (
            "Identidad",
            {
                "fields": (
                    "name",
                    "canonical_name",
                    "created_by",
                    "is_global",
                    "is_verified",
                    "is_active",
                    "visibility",
                    "data_quality_score",
                    "created_at",
                )
            },
        ),
        (
            "Clasificación alimentaria",
            {
                "fields": (
                    "food_group",
                    "food_subgroup",
                    "preparation_state",
                    "solver_enabled",
                )
            },
        ),
        (
            "Macronutrientes base por 100 g",
            {
                "fields": (
                    "protein",
                    "carbs",
                    "fat",
                    "total_kcal_display",
                )
            },
        ),
        (
            "Nutrientes extendidos por 100 g",
            {
                "fields": (
                    "fiber_g_per_100g",
                    "sugar_g_per_100g",
                    "saturated_fat_g_per_100g",
                    "sodium_mg_per_100g",
                )
            },
        ),
        (
            "Porciones sugeridas",
            {
                "fields": (
                    "default_portion_g",
                    "min_portion_g",
                    "max_portion_g",
                    "portion_step_g",
                )
            },
        ),
        (
            "Trazabilidad Food Catalog",
            {
                "fields": (
                    "catalog_sync_status",
                    "catalog_food_id",
                    "catalog_food_ref",
                    "catalog_snapshot_version",
                    "catalog_snapshot_created_at",
                    "catalog_snapshot_payload",
                ),
                "classes": ("collapse",),
                "description": (
                    "Referencia opcional a food_catalog. Estos campos no son "
                    "identificadores operativos para Meals, Solver ni MCP."
                ),
            },
        ),
    )

    inlines = (
        FoodSourceMetadataInline,
        FoodPortionInline,
        FoodAliasInline,
        FoodLocalizedNameInline,
    )

    actions = (
        mark_foods_as_core,
        mark_foods_as_extended,
        mark_foods_as_hidden,
        mark_foods_as_rejected,
        mark_foods_as_verified,
        mark_foods_as_unverified,
        mark_foods_as_active,
        mark_foods_as_inactive,
    )

    @admin.display(description="Total kcal / 100 g")
    def total_kcal_display(self, obj):
        return round(obj.total_kcal, 2)


@admin.register(FoodSourceMetadata)
class FoodSourceMetadataAdmin(admin.ModelAdmin):
    list_display = (
        "food",
        "source",
        "source_food_id",
        "source_dataset",
        "source_version",
        "imported_at",
        "last_synced_at",
    )

    list_filter = (
        "source",
        "source_dataset",
        "source_version",
        "imported_at",
        "last_synced_at",
    )

    search_fields = (
        "food__name",
        "food__canonical_name",
        "source_food_id",
        "source_dataset",
        "source_version",
    )

    readonly_fields = (
        "imported_at",
    )


@admin.register(FoodPortion)
class FoodPortionAdmin(admin.ModelAdmin):
    list_display = (
        "food",
        "label",
        "grams",
        "source",
        "is_default",
    )

    list_filter = (
        "source",
        "is_default",
    )

    search_fields = (
        "food__name",
        "food__canonical_name",
        "label",
    )


@admin.register(FoodAlias)
class FoodAliasAdmin(admin.ModelAdmin):
    list_display = (
        "food",
        "name",
        "normalized_name",
        "language",
        "country",
    )

    list_filter = (
        "language",
        "country",
    )

    search_fields = (
        "food__name",
        "food__canonical_name",
        "name",
        "normalized_name",
    )


@admin.register(FoodLocalizedName)
class FoodLocalizedNameAdmin(admin.ModelAdmin):
    list_display = (
        "food",
        "name",
        "normalized_name",
        "language",
        "country",
        "is_primary",
    )

    list_filter = (
        "language",
        "country",
        "is_primary",
    )

    search_fields = (
        "food__name",
        "food__canonical_name",
        "name",
        "normalized_name",
    )


@admin.register(FoodImportBatch)
class FoodImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "source",
        "source_version",
        "status",
        "total_rows",
        "imported_rows",
        "skipped_rows",
        "failed_rows",
        "started_at",
        "finished_at",
    )

    list_filter = (
        "source",
        "status",
        "started_at",
        "finished_at",
    )

    search_fields = (
        "source",
        "source_version",
        "notes",
    )

    readonly_fields = (
        "started_at",
    )


# =============================================================================
# Meals / daily plans
# =============================================================================

@admin.register(MealFood)
class MealFoodAdmin(admin.ModelAdmin):
    list_display = (
        "meal",
        "food",
        "quantity",
        "order",
    )

    list_filter = (
        "order",
    )

    search_fields = (
        "meal__name",
        "food__name",
    )


class DailyPlanMealInline(admin.TabularInline):
    model = DailyPlanMeal
    fields = (
        "note",
        "meal",
        "hour",
        "order",
    )
    extra = 1


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_by",
        "category",
        "is_public",
        "is_forkable",
        "is_copiable",
        "is_draft",
        "created_at",
    )

    list_filter = (
        "is_public",
        "is_forkable",
        "is_copiable",
        "is_draft",
        "created_at",
    )

    search_fields = (
        "name",
        "created_by__username",
        "created_by__email",
    )

    readonly_fields = (
        "created_at",
    )


@admin.register(DailyPlan)
class DailyPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_by",
        "category",
        "source",
        "is_public",
        "is_forkable",
        "is_copiable",
        "is_draft",
        "created_at",
    )

    list_filter = (
        "source",
        "is_public",
        "is_forkable",
        "is_copiable",
        "is_draft",
        "created_at",
    )

    search_fields = (
        "name",
        "created_by__username",
        "created_by__email",
    )

    readonly_fields = (
        "created_at",
    )

    inlines = (
        DailyPlanMealInline,
    )


@admin.register(DailyPlanMeal)
class DailyPlanMealAdmin(admin.ModelAdmin):
    list_display = (
        "dailyplan",
        "meal",
        "note",
        "hour",
        "order",
    )

    list_filter = (
        "hour",
    )

    search_fields = (
        "dailyplan__name",
        "meal__name",
        "note",
    )


# =============================================================================
# Nutrition proposals / AI review workflow
# =============================================================================

@admin.register(NutritionProposal)
class NutritionProposalAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "dailyplan",
        "status",
        "source",
        "created_by",
        "reviewed_by",
        "applied_by",
        "created_at",
        "reviewed_at",
        "applied_at",
    )

    list_filter = (
        "status",
        "source",
        "created_at",
        "reviewed_at",
        "applied_at",
    )

    search_fields = (
        "title",
        "summary",
        "dailyplan__name",
        "created_by__username",
        "reviewed_by__username",
        "applied_by__username",
    )

    readonly_fields = (
        "created_at",
        "reviewed_at",
        "applied_at",
    )


@admin.register(NutritionProposalAuditEvent)
class NutritionProposalAuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "proposal",
        "action",
        "actor",
        "status_before",
        "status_after",
        "created_at",
    )

    list_filter = (
        "action",
        "created_at",
    )

    search_fields = (
        "proposal__title",
        "actor__username",
        "message",
    )

    readonly_fields = (
        "created_at",
    )


# =============================================================================
# Programs / body weight tracking
# =============================================================================

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_by",
        "start_date",
        "end_date",
        "is_public",
        "is_forkable",
        "is_copiable",
        "is_draft",
        "created_at",
    )

    list_filter = (
        "is_public",
        "is_forkable",
        "is_copiable",
        "is_draft",
        "start_date",
        "end_date",
        "created_at",
    )

    search_fields = (
        "name",
        "created_by__username",
        "created_by__email",
    )

    readonly_fields = (
        "created_at",
    )


@admin.register(ProgramDay)
class ProgramDayAdmin(admin.ModelAdmin):
    list_display = (
        "program",
        "dailyplan",
        "date",
        "created_at",
    )

    list_filter = (
        "date",
        "created_at",
    )

    search_fields = (
        "program__name",
        "dailyplan__name",
    )

    readonly_fields = (
        "created_at",
    )


@admin.register(ProgramCalendarization)
class ProgramCalendarizationAdmin(admin.ModelAdmin):
    list_display = (
        "program_name_snapshot",
        "user",
        "start_date",
        "end_date",
        "timezone_name",
        "daily_notification_time",
        "status",
    )
    list_filter = ("status", "daily_notifications_enabled", "timezone_name")
    search_fields = ("program_name_snapshot", "user__username", "user__email")
    readonly_fields = (
        "program_name_snapshot",
        "start_date",
        "end_date",
        "timezone_name",
        "daily_notification_time",
        "activated_at",
        "paused_at",
        "completed_at",
        "cancelled_at",
        "created_at",
        "updated_at",
    )


@admin.register(CalendarizedDay)
class CalendarizedDayAdmin(admin.ModelAdmin):
    list_display = ("calendarization", "calendar_date", "week_number", "day_number", "has_plan")
    list_filter = ("calendar_date", "week_number")
    search_fields = ("calendarization__program_name_snapshot", "calendarization__user__username")
    readonly_fields = tuple(field.name for field in CalendarizedDay._meta.fields)


@admin.register(WebPushSubscription)
class WebPushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "device_label", "endpoint_fingerprint", "is_active", "last_success_at", "last_failure_at")
    list_filter = ("is_active", "last_success_at", "last_failure_at")
    search_fields = ("user__username", "user__email", "endpoint_fingerprint", "device_label")
    exclude = ("endpoint", "p256dh_key", "auth_key")
    readonly_fields = ("endpoint_fingerprint", "created_at", "updated_at", "last_success_at", "last_failure_at")


@admin.register(ScheduledNotificationEvent)
class ScheduledNotificationEventAdmin(admin.ModelAdmin):
    list_display = ("event_key", "event_type", "scheduled_for_utc", "status", "skip_reason")
    list_filter = ("event_type", "status", "timezone_name")
    search_fields = ("event_key", "calendarization__user__username")
    readonly_fields = tuple(field.name for field in ScheduledNotificationEvent._meta.fields)


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ("event", "subscription_fingerprint", "status", "attempt_count", "sent_at")
    list_filter = ("status", "sent_at")
    search_fields = ("event__event_key", "subscription_fingerprint")
    readonly_fields = tuple(field.name for field in NotificationDelivery._meta.fields)


@admin.register(WeightLog)
class WeightLogAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "date",
        "weight_kg",
        "source",
        "created_at",
    )

    list_filter = (
        "source",
        "date",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "created_at",
    )
