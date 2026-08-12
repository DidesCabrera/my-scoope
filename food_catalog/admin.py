"""Admin registrations for the master Food Catalog app."""

from django.contrib import admin, messages

from food_catalog.application.curation import transition_catalog_foods_status
from food_catalog.models import (
    CatalogCapabilityDefinition,
    CatalogClientRequirement,
    CatalogCurationCandidate,
    CatalogEnrichmentBatch,
    CatalogEnrichmentChange,
    CatalogFieldProposal,
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodCapability,
    CatalogFoodPortion,
    CatalogFoodSource,
    CatalogImportBatch,
    CatalogImportSourcePolicy,
    ExternalFoodReference,
    ExternalProviderFetchLog,
)


@admin.register(CatalogCapabilityDefinition)
class CatalogCapabilityDefinitionAdmin(admin.ModelAdmin):
    list_display = ("key", "schema_version", "nature", "maturity", "authority_requirement", "risk_level", "is_active")
    list_filter = ("nature", "maturity", "authority_requirement", "risk_level", "is_active")
    search_fields = ("key", "label")


@admin.register(CatalogClientRequirement)
class CatalogClientRequirementAdmin(admin.ModelAdmin):
    list_display = ("client_key", "requirement_version", "capability", "is_required", "is_active")
    list_filter = ("client_key", "is_required", "is_active")


@admin.register(CatalogFoodCapability)
class CatalogFoodCapabilityAdmin(admin.ModelAdmin):
    list_display = ("catalog_food", "definition", "assessment_status", "confidence", "generation_method", "updated_at")
    list_filter = ("assessment_status", "generation_method", "definition")
    search_fields = ("catalog_food__display_name", "definition__key")


@admin.register(CatalogEnrichmentBatch)
class CatalogEnrichmentBatchAdmin(admin.ModelAdmin):
    list_display = ("batch_ref", "environment", "status", "total_proposals", "valid_proposals", "applied_proposals", "created_at")
    list_filter = ("environment", "status", "executor_kind", "contract_version")
    search_fields = ("batch_ref", "reason", "instruction", "input_sha256", "manifest_sha256")
    readonly_fields = (
        "batch_ref", "input_sha256", "manifest_sha256", "manifest_payload", "status",
        "total_proposals", "valid_proposals", "applied_proposals", "failed_proposals",
        "dry_run_at", "approved_at", "applied_at", "reverted_at", "created_at", "updated_at",
    )


@admin.register(CatalogFieldProposal)
class CatalogFieldProposalAdmin(admin.ModelAdmin):
    list_display = ("batch", "catalog_food", "field_name", "status", "confidence", "risk_level", "authority_requirement")
    list_filter = ("status", "nature", "maturity", "risk_level", "authority_requirement", "generation_method")
    search_fields = ("catalog_food__display_name", "field_name", "rationale", "batch__batch_ref")
    readonly_fields = tuple(field.name for field in CatalogFieldProposal._meta.fields)


@admin.register(CatalogEnrichmentChange)
class CatalogEnrichmentChangeAdmin(admin.ModelAdmin):
    list_display = ("batch", "catalog_food", "field_name", "action", "actor", "created_at")
    list_filter = ("action", "field_name")
    search_fields = ("catalog_food__display_name", "batch__batch_ref", "reason")
    readonly_fields = tuple(field.name for field in CatalogEnrichmentChange._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CatalogFoodPortionInline(admin.TabularInline):
    model = CatalogFoodPortion
    extra = 0


class CatalogFoodAliasInline(admin.TabularInline):
    model = CatalogFoodAlias
    extra = 0


class CatalogFoodSourceInline(admin.TabularInline):
    model = CatalogFoodSource
    extra = 0
    fields = (
        "source_type",
        "source_name",
        "source_food_id",
        "source_dataset",
        "source_version",
        "license_status",
    )


@admin.register(CatalogFood)
class CatalogFoodAdmin(admin.ModelAdmin):
    actions = (
        "mark_as_pending_review",
        "mark_as_needs_more_evidence",
        "mark_as_reviewed",
        "mark_as_verified",
        "mark_as_published",
        "mark_as_rejected",
        "mark_as_deprecated",
        "mark_as_archived",
    )
    list_display = (
        "display_name",
        "brand_name",
        "status",
        "source_type",
        "data_quality_score",
        "solver_enabled",
        "preparation_state",
        "country",
        "updated_at",
    )
    list_filter = ("status", "source_type", "solver_enabled", "preparation_state", "is_branded", "country", "language")
    search_fields = ("display_name", "canonical_name", "brand_name", "aliases__name")
    readonly_fields = ("catalog_ref", "created_at", "updated_at")
    inlines = (CatalogFoodPortionInline, CatalogFoodAliasInline, CatalogFoodSourceInline)
    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "catalog_ref",
                    "catalog_version",
                    "display_name",
                    "canonical_name",
                    "brand_name",
                    "is_branded",
                    "language",
                    "country",
                    "food_group",
                    "food_subgroup",
                    "preparation_state",
                    "food_form",
                )
            },
        ),
        (
            "Solver readiness",
            {
                "fields": (
                    "solver_enabled",
                    "solver_min_portion_g",
                    "solver_max_portion_g",
                    "solver_portion_step_g",
                    "functional_roles",
                    "meal_affinities",
                    "dietary_tags",
                    "allergens",
                    "preparation_effort",
                    "cost_band",
                    "solver_capabilities_version",
                    "solver_feature_confidence",
                )
            },
        ),
        (
            "Nutrition per 100 g",
            {
                "fields": (
                    "protein_g_per_100g",
                    "carbs_g_per_100g",
                    "fat_g_per_100g",
                    "calories_kcal_per_100g",
                    "fiber_g_per_100g",
                    "sugar_g_per_100g",
                    "saturated_fat_g_per_100g",
                    "sodium_mg_per_100g",
                )
            },
        ),
        (
            "Curation",
            {
                "fields": (
                    "status",
                    "source_type",
                    "data_quality_score",
                    "confidence_score",
                    "created_by",
                    "reviewed_by",
                    "reviewed_at",
                    "published_at",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.action(description="Mark selected catalog foods as pending review")
    def mark_as_pending_review(self, request, queryset):
        self._apply_status_transition(
            request,
            queryset,
            CatalogFood.STATUS_PENDING_REVIEW,
            success_label="marked as pending review",
        )

    @admin.action(description="Mark selected catalog foods as needing more evidence")
    def mark_as_needs_more_evidence(self, request, queryset):
        self._apply_status_transition(
            request,
            queryset,
            CatalogFood.STATUS_NEEDS_MORE_EVIDENCE,
            success_label="marked as needing more evidence",
        )

    @admin.action(description="Mark selected catalog foods as reviewed")
    def mark_as_reviewed(self, request, queryset):
        self._apply_status_transition(
            request,
            queryset,
            CatalogFood.STATUS_REVIEWED,
            success_label="marked as reviewed",
        )

    @admin.action(description="Mark selected catalog foods as verified")
    def mark_as_verified(self, request, queryset):
        self._apply_status_transition(
            request,
            queryset,
            CatalogFood.STATUS_VERIFIED,
            success_label="marked as verified",
        )

    @admin.action(description="Publish selected catalog foods")
    def mark_as_published(self, request, queryset):
        self._apply_status_transition(
            request,
            queryset.prefetch_related("sources", "portions"),
            CatalogFood.STATUS_PUBLISHED,
            success_label="published",
        )

    @admin.action(description="Mark selected catalog foods as rejected")
    def mark_as_rejected(self, request, queryset):
        self._apply_status_transition(
            request,
            queryset,
            CatalogFood.STATUS_REJECTED,
            success_label="rejected",
        )

    @admin.action(description="Mark selected catalog foods as deprecated")
    def mark_as_deprecated(self, request, queryset):
        self._apply_status_transition(
            request,
            queryset,
            CatalogFood.STATUS_DEPRECATED,
            success_label="marked as deprecated",
        )

    @admin.action(description="Archive selected catalog foods")
    def mark_as_archived(self, request, queryset):
        self._apply_status_transition(
            request,
            queryset,
            CatalogFood.STATUS_ARCHIVED,
            success_label="archived",
        )

    def _apply_status_transition(self, request, queryset, target_status: str, *, success_label: str):
        result = transition_catalog_foods_status(
            queryset,
            target_status,
            user=getattr(request, "user", None),
        )

        if result.changed_count:
            self.message_user(
                request,
                f"{result.changed_count} catalog foods {success_label}.",
            )

        if result.blocked:
            self.message_user(
                request,
                "Curation transition blocked for " + " | ".join(result.blocked),
                level=messages.WARNING,
            )


@admin.register(CatalogImportBatch)
class CatalogImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "source_name",
        "source_type",
        "source_version",
        "status",
        "is_dry_run",
        "total_rows",
        "imported_rows",
        "failed_rows",
        "started_at",
    )
    list_filter = ("source_type", "status", "is_dry_run")
    search_fields = ("source_name", "source_version", "notes")
    readonly_fields = ("started_at",)


@admin.register(CatalogImportSourcePolicy)
class CatalogImportSourcePolicyAdmin(admin.ModelAdmin):
    list_display = ("source_name", "source_type", "is_enabled", "scale_approved", "kill_switch", "max_batch_rows", "approved_at")
    list_filter = ("source_type", "is_enabled", "scale_approved", "kill_switch")
    search_fields = ("source_name", "approval_reason")


@admin.register(CatalogFoodPortion)
class CatalogFoodPortionAdmin(admin.ModelAdmin):
    list_display = ("catalog_food", "label", "grams", "is_default", "source")
    list_filter = ("is_default", "source")
    search_fields = ("catalog_food__display_name", "label")


@admin.register(CatalogFoodAlias)
class CatalogFoodAliasAdmin(admin.ModelAdmin):
    list_display = ("name", "catalog_food", "alias_type", "language", "country", "is_primary")
    list_filter = ("alias_type", "language", "country", "is_primary")
    search_fields = ("name", "normalized_name", "catalog_food__display_name")


@admin.register(CatalogFoodSource)
class CatalogFoodSourceAdmin(admin.ModelAdmin):
    list_display = (
        "catalog_food",
        "source_name",
        "source_type",
        "source_food_id",
        "license_status",
        "imported_at",
    )
    list_filter = ("source_type", "license_status", "source_name")
    search_fields = (
        "catalog_food__display_name",
        "source_name",
        "source_food_id",
        "source_dataset",
    )
    readonly_fields = ("imported_at",)



@admin.register(CatalogCurationCandidate)
class CatalogCurationCandidateAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "brand_name",
        "provider",
        "status",
        "reason",
        "priority",
        "seen_count_at_creation",
        "selected_count_at_creation",
        "updated_at",
    )
    list_filter = ("status", "reason", "provider", "priority")
    search_fields = ("display_name", "brand_name", "external_food_id", "external_serving_id", "notes")
    readonly_fields = (
        "provider",
        "external_food_id",
        "external_serving_id",
        "source_url",
        "attribution_text",
        "seen_count_at_creation",
        "selected_count_at_creation",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "External reference",
            {
                "fields": (
                    "external_reference",
                    "provider",
                    "external_food_id",
                    "external_serving_id",
                    "display_name",
                    "brand_name",
                    "source_url",
                    "attribution_text",
                )
            },
        ),
        (
            "Curation queue",
            {
                "fields": (
                    "status",
                    "reason",
                    "priority",
                    "seen_count_at_creation",
                    "selected_count_at_creation",
                    "notes",
                    "created_by",
                    "reviewed_by",
                    "reviewed_at",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )



@admin.register(ExternalFoodReference)
class ExternalFoodReferenceAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "display_name",
        "brand_name",
        "external_food_id",
        "external_serving_id",
        "seen_count",
        "selected_count",
        "expires_at",
        "is_active",
    )
    list_filter = ("provider", "is_active", "expires_at")
    search_fields = ("display_name", "brand_name", "external_food_id", "external_serving_id")
    readonly_fields = (
        "first_seen_at",
        "last_seen_at",
        "last_fetched_at",
        "raw_payload_hash",
        "detail_payload_hash",
    )


@admin.register(ExternalProviderFetchLog)
class ExternalProviderFetchLogAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "lookup_type",
        "status",
        "query",
        "external_food_id",
        "external_serving_id",
        "status_code",
        "fetched_at",
        "expires_at",
    )
    list_filter = ("provider", "lookup_type", "status")
    search_fields = ("query", "external_food_id", "external_serving_id", "error_message")
    readonly_fields = ("fetched_at", "raw_payload_hash")
