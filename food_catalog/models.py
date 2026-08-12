"""Master Food Catalog models.

These models belong to the independent Food Catalog app. They represent the
master catalog and its curation evidence only; operational nutrition features
continue to use ``notas.Food`` until a later internal snapshot protocol writes
or refreshes operational foods explicitly.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class CatalogFood(models.Model):
    """Master, curated food record owned by Food Catalog.

    ``CatalogFood`` is not an operational food. Meals, DailyPlans, Programs,
    Proposals, Comparators, Solver and MCP must keep using ``notas.Food``.
    """

    STATUS_EXTERNAL_CANDIDATE = "external_candidate"
    STATUS_MANUAL_CANDIDATE = "manual_candidate"
    STATUS_BRAND_SUBMITTED = "brand_submitted"
    STATUS_NORMALIZED = "normalized"
    STATUS_PENDING_REVIEW = "pending_review"
    STATUS_NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    STATUS_REVIEWED = "reviewed"
    STATUS_VERIFIED = "verified"
    STATUS_PUBLISHED = "published"
    STATUS_REJECTED = "rejected"
    STATUS_DEPRECATED = "deprecated"
    STATUS_ARCHIVED = "archived"

    STATUS_CHOICES = [
        (STATUS_EXTERNAL_CANDIDATE, "External candidate"),
        (STATUS_MANUAL_CANDIDATE, "Manual candidate"),
        (STATUS_BRAND_SUBMITTED, "Brand submitted"),
        (STATUS_NORMALIZED, "Normalized"),
        (STATUS_PENDING_REVIEW, "Pending review"),
        (STATUS_NEEDS_MORE_EVIDENCE, "Needs more evidence"),
        (STATUS_REVIEWED, "Reviewed"),
        (STATUS_VERIFIED, "Verified"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_DEPRECATED, "Deprecated"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    SOURCE_NATURAL_VERIFIED = "natural_verified"
    SOURCE_USDA = "usda"
    SOURCE_BRAND_SUBMITTED = "brand_submitted"
    SOURCE_USER_CREATED = "user_created"
    SOURCE_EXTERNAL_TEMPORARY = "external_temporary"
    SOURCE_FATSECRET = "fatsecret"
    SOURCE_OPEN_FOOD_FACTS = "open_food_facts"
    SOURCE_ADMIN_IMPORT = "admin_import"

    SOURCE_TYPE_CHOICES = [
        (SOURCE_NATURAL_VERIFIED, "Natural verified"),
        (SOURCE_USDA, "USDA FoodData Central"),
        (SOURCE_BRAND_SUBMITTED, "Brand submitted"),
        (SOURCE_USER_CREATED, "User created"),
        (SOURCE_EXTERNAL_TEMPORARY, "External temporary"),
        (SOURCE_FATSECRET, "FatSecret"),
        (SOURCE_OPEN_FOOD_FACTS, "Open Food Facts"),
        (SOURCE_ADMIN_IMPORT, "Admin import"),
    ]

    PREPARATION_UNKNOWN = "unknown"
    PREPARATION_RAW = "raw"
    PREPARATION_COOKED = "cooked"
    PREPARATION_DRY = "dry"
    PREPARATION_HYDRATED = "hydrated"
    PREPARATION_READY_TO_EAT = "ready_to_eat"

    PREPARATION_STATE_CHOICES = [
        (PREPARATION_UNKNOWN, "Unknown"),
        (PREPARATION_RAW, "Raw"),
        (PREPARATION_COOKED, "Cooked"),
        (PREPARATION_DRY, "Dry"),
        (PREPARATION_HYDRATED, "Hydrated"),
        (PREPARATION_READY_TO_EAT, "Ready to eat"),
    ]

    FOOD_FORM_UNKNOWN = "unknown"
    FOOD_FORM_INGREDIENT = "ingredient"
    FOOD_FORM_MIXED_DISH = "mixed_dish"
    FOOD_FORM_BEVERAGE = "beverage"
    FOOD_FORM_CONDIMENT = "condiment"

    FOOD_FORM_CHOICES = [
        (FOOD_FORM_UNKNOWN, "Unknown"),
        (FOOD_FORM_INGREDIENT, "Ingredient"),
        (FOOD_FORM_MIXED_DISH, "Mixed dish"),
        (FOOD_FORM_BEVERAGE, "Beverage"),
        (FOOD_FORM_CONDIMENT, "Condiment"),
    ]

    PREPARATION_EFFORT_UNKNOWN = "unknown"
    PREPARATION_EFFORT_NONE = "none"
    PREPARATION_EFFORT_LOW = "low"
    PREPARATION_EFFORT_MEDIUM = "medium"
    PREPARATION_EFFORT_HIGH = "high"

    PREPARATION_EFFORT_CHOICES = [
        (PREPARATION_EFFORT_UNKNOWN, "Unknown"),
        (PREPARATION_EFFORT_NONE, "None"),
        (PREPARATION_EFFORT_LOW, "Low"),
        (PREPARATION_EFFORT_MEDIUM, "Medium"),
        (PREPARATION_EFFORT_HIGH, "High"),
    ]

    COST_BAND_UNKNOWN = "unknown"
    COST_BAND_LOW = "low"
    COST_BAND_MEDIUM = "medium"
    COST_BAND_HIGH = "high"

    COST_BAND_CHOICES = [
        (COST_BAND_UNKNOWN, "Unknown"),
        (COST_BAND_LOW, "Low"),
        (COST_BAND_MEDIUM, "Medium"),
        (COST_BAND_HIGH, "High"),
    ]

    catalog_ref = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Stable master catalog reference. Not an operational food ID.",
    )

    catalog_version = models.CharField(
        max_length=64,
        default="v1",
        help_text="Current master catalog version label for publication/snapshot traceability.",
    )

    display_name = models.CharField(
        max_length=255,
        help_text="Human-friendly name for curators and eventual publication.",
    )

    canonical_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Normalized name for deduplication and matching inside Food Catalog.",
    )

    brand_name = models.CharField(
        max_length=160,
        blank=True,
    )

    is_branded = models.BooleanField(default=False)

    language = models.CharField(
        max_length=10,
        default="es",
    )

    country = models.CharField(
        max_length=10,
        blank=True,
        help_text="Optional country/region code. Example: CL, AR, MX.",
    )

    food_group = models.CharField(
        max_length=120,
        blank=True,
    )

    food_subgroup = models.CharField(
        max_length=120,
        blank=True,
    )

    preparation_state = models.CharField(
        max_length=30,
        choices=PREPARATION_STATE_CHOICES,
        default=PREPARATION_UNKNOWN,
        help_text=(
            "Semantic state used for curation and solver safety. Example: raw, "
            "cooked, dry, hydrated or ready_to_eat. Avoids mixing raw/cooked data."
        ),
    )

    food_form = models.CharField(
        max_length=30,
        choices=FOOD_FORM_CHOICES,
        default=FOOD_FORM_UNKNOWN,
        help_text="Curated culinary form used by meal grammar after operational snapshot.",
    )

    functional_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Versioned multi-role capability labels; no single role is treated as complete truth.",
    )

    meal_affinities = models.JSONField(
        default=list,
        blank=True,
        help_text="Curated meal-kind affinities such as breakfast, snack, main or dinner.",
    )

    dietary_tags = models.JSONField(default=list, blank=True)
    allergens = models.JSONField(default=list, blank=True)

    preparation_effort = models.CharField(
        max_length=20,
        choices=PREPARATION_EFFORT_CHOICES,
        default=PREPARATION_EFFORT_UNKNOWN,
    )

    cost_band = models.CharField(
        max_length=20,
        choices=COST_BAND_CHOICES,
        default=COST_BAND_UNKNOWN,
    )

    solver_capabilities_version = models.CharField(
        max_length=64,
        default="solver_food_capabilities.v1",
    )

    solver_feature_confidence = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-feature confidence values from 0 to 100 for solver projections.",
    )

    solver_enabled = models.BooleanField(
        default=False,
        help_text=(
            "If true, this master food is eligible to become an operational "
            "solver candidate after publication/snapshot."
        ),
    )

    solver_min_portion_g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="Optional explicit minimum portion for future optimization.",
    )

    solver_max_portion_g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="Optional explicit maximum portion for future optimization.",
    )

    solver_portion_step_g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="Optional explicit portion increment for future optimization.",
    )

    protein_g_per_100g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
    )

    carbs_g_per_100g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
    )

    fat_g_per_100g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
    )

    calories_kcal_per_100g = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Optional label/source kcal per 100 g. Operational kcal remains snapshot-specific.",
    )

    fiber_g_per_100g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    sugar_g_per_100g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    saturated_fat_g_per_100g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    sodium_mg_per_100g = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    status = models.CharField(
        max_length=40,
        choices=STATUS_CHOICES,
        default=STATUS_MANUAL_CANDIDATE,
    )

    source_type = models.CharField(
        max_length=40,
        choices=SOURCE_TYPE_CHOICES,
        default=SOURCE_ADMIN_IMPORT,
        help_text="High-level origin category for curation and governance.",
    )

    data_quality_score = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_catalog_foods",
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_catalog_foods",
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Catalog food"
        verbose_name_plural = "Catalog foods"
        ordering = ["display_name", "brand_name", "country"]
        indexes = [
            models.Index(fields=["status", "source_type"], name="catalog_food_status_source_idx"),
            models.Index(fields=["canonical_name"], name="catalog_food_canonical_idx"),
            models.Index(fields=["display_name"], name="catalog_food_display_idx"),
            models.Index(fields=["solver_enabled", "status"], name="catalog_food_solver_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["canonical_name", "brand_name", "country"],
                condition=~models.Q(canonical_name=""),
                name="unique_catalog_food_canonical_brand_country",
            ),
        ]

    def __str__(self) -> str:
        if self.brand_name:
            return f"{self.display_name} · {self.brand_name}"
        return self.display_name

    @property
    def is_published(self) -> bool:
        return self.status == self.STATUS_PUBLISHED

    @property
    def macro_calories_kcal(self) -> Decimal:
        return (
            self.protein_g_per_100g * Decimal("4")
            + self.carbs_g_per_100g * Decimal("4")
            + self.fat_g_per_100g * Decimal("9")
        )


class CatalogFoodPortion(models.Model):
    """Serving option attached to a master catalog food."""

    catalog_food = models.ForeignKey(
        CatalogFood,
        on_delete=models.CASCADE,
        related_name="portions",
    )

    label = models.CharField(max_length=120)

    grams = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )

    source = models.CharField(
        max_length=80,
        blank=True,
    )

    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Catalog food portion"
        verbose_name_plural = "Catalog food portions"
        ordering = ["catalog_food", "-is_default", "label"]
        constraints = [
            models.UniqueConstraint(
                fields=["catalog_food", "label"],
                name="unique_catalog_food_portion_label",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.catalog_food} · {self.label} = {self.grams} g"


class CatalogFoodAlias(models.Model):
    """Search alias or localized name for a master catalog food."""

    ALIAS_SEARCH = "search"
    ALIAS_COMMON = "common"
    ALIAS_LOCALIZED = "localized"

    ALIAS_TYPE_CHOICES = [
        (ALIAS_SEARCH, "Search"),
        (ALIAS_COMMON, "Common"),
        (ALIAS_LOCALIZED, "Localized"),
    ]

    catalog_food = models.ForeignKey(
        CatalogFood,
        on_delete=models.CASCADE,
        related_name="aliases",
    )

    name = models.CharField(max_length=255)

    normalized_name = models.CharField(
        max_length=255,
        blank=True,
    )

    alias_type = models.CharField(
        max_length=30,
        choices=ALIAS_TYPE_CHOICES,
        default=ALIAS_SEARCH,
    )

    language = models.CharField(
        max_length=10,
        default="es",
    )

    country = models.CharField(
        max_length=10,
        blank=True,
    )

    is_primary = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Catalog food alias"
        verbose_name_plural = "Catalog food aliases"
        ordering = ["catalog_food", "language", "country", "-is_primary", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["catalog_food", "normalized_name", "language", "country"],
                condition=~models.Q(normalized_name=""),
                name="unique_catalog_food_alias_language_country",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} → {self.catalog_food}"


class CatalogFoodSource(models.Model):
    """Traceable source/evidence record for a master catalog food."""

    LICENSE_ALLOWED = "allowed"
    LICENSE_NEEDS_REVIEW = "needs_review"
    LICENSE_RESTRICTED = "restricted"
    LICENSE_UNKNOWN = "unknown"

    LICENSE_STATUS_CHOICES = [
        (LICENSE_ALLOWED, "Allowed"),
        (LICENSE_NEEDS_REVIEW, "Needs review"),
        (LICENSE_RESTRICTED, "Restricted"),
        (LICENSE_UNKNOWN, "Unknown"),
    ]

    catalog_food = models.ForeignKey(
        CatalogFood,
        on_delete=models.CASCADE,
        related_name="sources",
    )

    import_batch = models.ForeignKey(
        "CatalogImportBatch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="food_sources",
    )

    source_type = models.CharField(
        max_length=40,
        choices=CatalogFood.SOURCE_TYPE_CHOICES,
    )

    source_name = models.CharField(max_length=160)

    source_food_id = models.CharField(
        max_length=160,
        blank=True,
    )

    source_dataset = models.CharField(
        max_length=160,
        blank=True,
    )

    source_version = models.CharField(
        max_length=160,
        blank=True,
    )

    source_url = models.URLField(blank=True)

    raw_payload_hash = models.CharField(max_length=128, blank=True)
    normalized_payload_hash = models.CharField(max_length=128, blank=True)

    license_name = models.CharField(max_length=160, blank=True)
    license_status = models.CharField(
        max_length=40,
        choices=LICENSE_STATUS_CHOICES,
        default=LICENSE_UNKNOWN,
    )
    attribution = models.TextField(blank=True)

    evidence_payload = models.JSONField(default=dict, blank=True)

    imported_at = models.DateTimeField(auto_now_add=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Catalog food source"
        verbose_name_plural = "Catalog food sources"
        ordering = ["catalog_food", "source_name", "source_food_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_name", "source_food_id"],
                condition=~models.Q(source_food_id=""),
                name="unique_catalog_food_source_external_id",
            ),
        ]

    def __str__(self) -> str:
        external_id = f" · {self.source_food_id}" if self.source_food_id else ""
        return f"{self.catalog_food} · {self.source_name}{external_id}"


EXTERNAL_FOOD_PROVIDER_CHOICES = [
    (CatalogFood.SOURCE_FATSECRET, "FatSecret"),
    (CatalogFood.SOURCE_OPEN_FOOD_FACTS, "Open Food Facts"),
]


class ExternalFoodReference(models.Model):
    """Stored reference to an external provider food/serving.

    This model intentionally stores provider identifiers, display metadata,
    attribution and payload hashes only. It is not a curated ``CatalogFood`` and
    it is not an operational ``notas.Food``. Provider nutrition payloads must be
    fetched again or handled by provider-specific cache rules before use.
    """

    provider = models.CharField(
        max_length=40,
        choices=EXTERNAL_FOOD_PROVIDER_CHOICES,
        help_text="External provider key, for example fatsecret.",
    )

    external_food_id = models.CharField(max_length=160)
    external_serving_id = models.CharField(max_length=160, blank=True)

    display_name = models.CharField(max_length=255)
    brand_name = models.CharField(max_length=160, blank=True)
    source_url = models.URLField(blank=True)
    attribution_text = models.TextField(blank=True)

    raw_payload_hash = models.CharField(
        max_length=128,
        blank=True,
        help_text="Hash of the latest provider payload used for traceability. Raw payload is not stored here.",
    )
    detail_payload_hash = models.CharField(
        max_length=128,
        blank=True,
        help_text="Optional hash of the latest detail payload. Raw payload is not stored here.",
    )

    seen_count = models.PositiveIntegerField(default=0)
    selected_count = models.PositiveIntegerField(default=0)

    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When provider data must be refreshed before display/calculation.",
    )

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "External food reference"
        verbose_name_plural = "External food references"
        ordering = ["provider", "display_name", "external_food_id", "external_serving_id"]
        indexes = [
            models.Index(fields=["provider", "external_food_id"], name="ext_food_ref_provider_food_idx"),
            models.Index(fields=["provider", "expires_at"], name="ext_food_ref_provider_exp_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_food_id", "external_serving_id"],
                name="unique_external_food_reference",
            ),
        ]

    def __str__(self) -> str:
        serving = f" · serving {self.external_serving_id}" if self.external_serving_id else ""
        return f"{self.provider}:{self.external_food_id}{serving} · {self.display_name}"


class ExternalProviderFetchLog(models.Model):
    """Trace one external provider lookup without persisting provider payloads."""

    LOOKUP_SEARCH = "search"
    LOOKUP_DETAIL = "detail"
    LOOKUP_SERVING = "serving"

    LOOKUP_TYPE_CHOICES = [
        (LOOKUP_SEARCH, "Search"),
        (LOOKUP_DETAIL, "Detail"),
        (LOOKUP_SERVING, "Serving"),
    ]

    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    provider = models.CharField(max_length=40, choices=EXTERNAL_FOOD_PROVIDER_CHOICES)
    lookup_type = models.CharField(max_length=30, choices=LOOKUP_TYPE_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)

    query = models.CharField(max_length=255, blank=True)
    external_food_id = models.CharField(max_length=160, blank=True)
    external_serving_id = models.CharField(max_length=160, blank=True)

    status_code = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    raw_payload_hash = models.CharField(max_length=128, blank=True)

    fetched_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "External provider fetch log"
        verbose_name_plural = "External provider fetch logs"
        ordering = ["-fetched_at"]
        indexes = [
            models.Index(fields=["provider", "lookup_type", "status"], name="ext_fetch_provider_type_idx"),
            models.Index(fields=["provider", "fetched_at"], name="ext_fetch_provider_time_idx"),
        ]

    def __str__(self) -> str:
        target = self.query or self.external_food_id or "lookup"
        return f"{self.provider} · {self.lookup_type} · {self.status} · {target}"


class CatalogCurationCandidate(models.Model):
    """Queue entry for turning external references into curated catalog work.

    A candidate is not a ``CatalogFood`` and is not an operational
    ``notas.Food``. It is a curator-facing work item created from external
    lookup demand so frequently seen/selected provider foods can later be
    reviewed, sourced and normalized into the master catalog.
    """

    STATUS_QUEUED = "queued"
    STATUS_IN_REVIEW = "in_review"
    STATUS_NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    STATUS_APPROVED_FOR_CURATION = "approved_for_curation"
    STATUS_REJECTED = "rejected"
    STATUS_ARCHIVED = "archived"

    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_IN_REVIEW, "In review"),
        (STATUS_NEEDS_MORE_EVIDENCE, "Needs more evidence"),
        (STATUS_APPROVED_FOR_CURATION, "Approved for curation"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    REASON_EXTERNAL_SELECTED = "external_selected"
    REASON_EXTERNAL_DEMAND = "external_demand"
    REASON_MANUAL_REVIEW = "manual_review"

    REASON_CHOICES = [
        (REASON_EXTERNAL_SELECTED, "External selected"),
        (REASON_EXTERNAL_DEMAND, "External demand"),
        (REASON_MANUAL_REVIEW, "Manual review"),
    ]

    external_reference = models.ForeignKey(
        ExternalFoodReference,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="curation_candidates",
        help_text="External lookup reference that triggered this curation work item.",
    )

    provider = models.CharField(max_length=40, choices=EXTERNAL_FOOD_PROVIDER_CHOICES)
    external_food_id = models.CharField(max_length=160, blank=True)
    external_serving_id = models.CharField(max_length=160, blank=True)

    display_name = models.CharField(max_length=255)
    brand_name = models.CharField(max_length=160, blank=True)
    source_url = models.URLField(blank=True)
    attribution_text = models.TextField(blank=True)

    status = models.CharField(
        max_length=40,
        choices=STATUS_CHOICES,
        default=STATUS_QUEUED,
    )
    reason = models.CharField(
        max_length=40,
        choices=REASON_CHOICES,
        default=REASON_EXTERNAL_DEMAND,
    )
    priority = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Curator priority from 0 to 100. Higher means more urgent.",
    )

    seen_count_at_creation = models.PositiveIntegerField(default=0)
    selected_count_at_creation = models.PositiveIntegerField(default=0)

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_catalog_curation_candidates",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_catalog_curation_candidates",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Catalog curation candidate"
        verbose_name_plural = "Catalog curation candidates"
        ordering = ["-priority", "status", "display_name"]
        indexes = [
            models.Index(fields=["status", "priority"], name="cat_curation_status_prio_idx"),
            models.Index(fields=["provider", "external_food_id"], name="cat_curation_provider_food_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["external_reference"],
                condition=models.Q(external_reference__isnull=False),
                name="unique_catalog_curation_external_ref",
            ),
        ]

    def __str__(self) -> str:
        brand = f" · {self.brand_name}" if self.brand_name else ""
        return f"{self.display_name}{brand} · {self.status}"


class CatalogImportBatch(models.Model):
    """Import/curation batch for Food Catalog candidates and sources."""

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_COMPLETED_WITH_ERRORS = "completed_with_errors"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_COMPLETED_WITH_ERRORS, "Completed with errors"),
        (STATUS_FAILED, "Failed"),
    ]

    source_type = models.CharField(
        max_length=40,
        choices=CatalogFood.SOURCE_TYPE_CHOICES,
    )

    source_name = models.CharField(max_length=160)
    source_version = models.CharField(max_length=160, blank=True)

    status = models.CharField(
        max_length=40,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    is_dry_run = models.BooleanField(default=False)

    dry_run_batch = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="applied_batches",
        help_text="Completed equivalent dry-run that authorized this mutating batch.",
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_catalog_import_batches",
    )

    reason = models.TextField(blank=True)
    input_sha256 = models.CharField(max_length=64, blank=True)
    parameters_payload = models.JSONField(default=dict, blank=True)

    total_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)
    skipped_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)

    notes = models.TextField(blank=True)
    summary_payload = models.JSONField(default=dict, blank=True)

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Catalog import batch"
        verbose_name_plural = "Catalog import batches"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["source_type", "status"], name="cat_batch_src_status_idx"),
        ]

    def __str__(self) -> str:
        version = f" · {self.source_version}" if self.source_version else ""
        return f"{self.source_name}{version} · {self.status}"


class CatalogImportSourcePolicy(models.Model):
    """Explicit gate for scaling one persistent source beyond its sample size."""

    source_type = models.CharField(max_length=40, choices=CatalogFood.SOURCE_TYPE_CHOICES)
    source_name = models.CharField(max_length=160)
    is_enabled = models.BooleanField(default=True)
    scale_approved = models.BooleanField(default=False)
    kill_switch = models.BooleanField(default=False)
    max_batch_rows = models.PositiveIntegerField(default=10)
    approval_reason = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_catalog_import_source_policies",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source_type", "source_name"], name="unique_catalog_import_source_policy")
        ]
        ordering = ["source_type", "source_name"]

    def __str__(self) -> str:
        return f"{self.source_name} · max {self.max_batch_rows}"


class CatalogCapabilityDefinition(models.Model):
    """Versioned definition of an evolvable Food Catalog capability.

    The independent dimensions intentionally avoid conflating who consumes a
    value with what kind of value it is, how it was obtained, or how mature the
    contract currently is.
    """

    NATURE_FACTUAL = "factual"
    NATURE_OPERATIONAL = "operational"
    NATURE_SEMANTIC = "semantic"
    NATURE_DERIVED = "derived"
    NATURE_COMMERCIAL_CONTEXT = "commercial_context"
    NATURE_CHOICES = [
        (NATURE_FACTUAL, "Factual"),
        (NATURE_OPERATIONAL, "Operational"),
        (NATURE_SEMANTIC, "Semantic"),
        (NATURE_DERIVED, "Derived"),
        (NATURE_COMMERCIAL_CONTEXT, "Commercial context"),
    ]

    MATURITY_EXPERIMENTAL = "experimental"
    MATURITY_CANDIDATE = "candidate"
    MATURITY_STABLE = "stable"
    MATURITY_DEPRECATED = "deprecated"
    MATURITY_RETIRED = "retired"
    MATURITY_CHOICES = [
        (MATURITY_EXPERIMENTAL, "Experimental"),
        (MATURITY_CANDIDATE, "Candidate"),
        (MATURITY_STABLE, "Stable"),
        (MATURITY_DEPRECATED, "Deprecated"),
        (MATURITY_RETIRED, "Retired"),
    ]

    AUTHORITY_RULE_AUTO = "rule_auto_apply"
    AUTHORITY_INTERNAL = "internal_review"
    AUTHORITY_EXPERT = "expert_review"
    AUTHORITY_EXTERNAL = "external_evidence_required"
    AUTHORITY_LEGAL = "legal_review_required"
    AUTHORITY_CHOICES = [
        (AUTHORITY_RULE_AUTO, "Rule auto-apply"),
        (AUTHORITY_INTERNAL, "Internal review"),
        (AUTHORITY_EXPERT, "Expert review"),
        (AUTHORITY_EXTERNAL, "External evidence required"),
        (AUTHORITY_LEGAL, "Legal review required"),
    ]

    RISK_LOW = "low"
    RISK_MEDIUM = "medium"
    RISK_HIGH = "high"
    RISK_CRITICAL = "critical"
    RISK_CHOICES = [
        (RISK_LOW, "Low"),
        (RISK_MEDIUM, "Medium"),
        (RISK_HIGH, "High"),
        (RISK_CRITICAL, "Critical"),
    ]

    key = models.SlugField(max_length=120)
    schema_version = models.CharField(max_length=64, default="v1")
    label = models.CharField(max_length=160)
    data_type = models.CharField(max_length=40)
    nature = models.CharField(max_length=40, choices=NATURE_CHOICES)
    maturity = models.CharField(max_length=30, choices=MATURITY_CHOICES, default=MATURITY_EXPERIMENTAL)
    consumers = models.JSONField(default=list, blank=True)
    allowed_values = models.JSONField(default=list, blank=True)
    authority_requirement = models.CharField(max_length=40, choices=AUTHORITY_CHOICES)
    risk_level = models.CharField(max_length=20, choices=RISK_CHOICES, default=RISK_MEDIUM)
    scope_rules = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["key", "schema_version"], name="unique_catalog_capability_version")
        ]
        ordering = ["key", "schema_version"]

    def __str__(self) -> str:
        return f"{self.key}@{self.schema_version}"


class CatalogClientRequirement(models.Model):
    """A client declares a need; Food Catalog retains authority over its value."""

    client_key = models.SlugField(max_length=80)
    requirement_version = models.CharField(max_length=64)
    capability = models.ForeignKey(
        CatalogCapabilityDefinition,
        on_delete=models.PROTECT,
        related_name="client_requirements",
    )
    is_required = models.BooleanField(default=False)
    absence_behavior = models.CharField(max_length=80, blank=True)
    operational_destination = models.CharField(max_length=160, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client_key", "requirement_version", "capability"],
                name="unique_catalog_client_requirement",
            )
        ]


class CatalogFoodCapability(models.Model):
    """Assessed value of an evolvable capability for one master food."""

    STATUS_UNASSESSED = "unassessed"
    STATUS_PROPOSED = "proposed"
    STATUS_CONFIRMED_VALUE = "confirmed_value"
    STATUS_CONFIRMED_NONE = "confirmed_none"
    STATUS_NOT_APPLICABLE = "not_applicable"
    STATUS_CONFLICTING = "conflicting_evidence"
    STATUS_SUPERSEDED = "superseded"
    STATUS_CHOICES = [
        (STATUS_UNASSESSED, "Unassessed"),
        (STATUS_PROPOSED, "Proposed"),
        (STATUS_CONFIRMED_VALUE, "Confirmed value"),
        (STATUS_CONFIRMED_NONE, "Confirmed none"),
        (STATUS_NOT_APPLICABLE, "Not applicable"),
        (STATUS_CONFLICTING, "Conflicting evidence"),
        (STATUS_SUPERSEDED, "Superseded"),
    ]

    catalog_food = models.ForeignKey(CatalogFood, on_delete=models.CASCADE, related_name="capability_values")
    definition = models.ForeignKey(
        CatalogCapabilityDefinition, on_delete=models.PROTECT, related_name="food_values"
    )
    value = models.JSONField(null=True, blank=True)
    assessment_status = models.CharField(max_length=40, choices=STATUS_CHOICES, default=STATUS_UNASSESSED)
    provenance = models.JSONField(default=list, blank=True)
    generation_method = models.CharField(max_length=40, blank=True)
    evidence_references = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    policy_version = models.CharField(max_length=80, blank=True)
    scope = models.JSONField(default=dict, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    review_due_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="catalog_capability_decisions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["catalog_food", "definition"], name="unique_catalog_food_capability")
        ]


class CatalogEnrichmentBatch(models.Model):
    """One bounded, reproducible Codex-assisted enrichment instance."""

    STATUS_DRAFT = "draft"
    STATUS_GENERATED = "generated"
    STATUS_DRY_RUN_VALID = "dry_run_valid"
    STATUS_DRY_RUN_FAILED = "dry_run_failed"
    STATUS_APPROVED = "approved_for_apply"
    STATUS_APPLIED = "applied"
    STATUS_PARTIALLY_APPLIED = "partially_applied"
    STATUS_REVERTED = "reverted"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [(value, value.replace("_", " ").title()) for value in (
        STATUS_DRAFT, STATUS_GENERATED, STATUS_DRY_RUN_VALID, STATUS_DRY_RUN_FAILED,
        STATUS_APPROVED, STATUS_APPLIED, STATUS_PARTIALLY_APPLIED, STATUS_REVERTED, STATUS_CANCELLED,
    )]

    batch_ref = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    environment = models.CharField(max_length=30)
    reason = models.TextField()
    scope_payload = models.JSONField(default=dict)
    instruction = models.TextField(blank=True)
    executor_kind = models.CharField(max_length=40, default="codex_assisted")
    contract_version = models.CharField(max_length=64, default="catalog-enrichment.v1")
    policy_version = models.CharField(max_length=64, default="catalog-enrichment-policy.v1")
    input_sha256 = models.CharField(max_length=64)
    manifest_sha256 = models.CharField(max_length=64, blank=True)
    manifest_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    total_proposals = models.PositiveIntegerField(default=0)
    valid_proposals = models.PositiveIntegerField(default=0)
    applied_proposals = models.PositiveIntegerField(default=0)
    failed_proposals = models.PositiveIntegerField(default=0)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="requested_catalog_enrichment_batches"
    )
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="applied_catalog_enrichment_batches"
    )
    dry_run_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    reverted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class CatalogFieldProposal(models.Model):
    """One field-level proposed decision; proposals never imply publication."""

    STATUS_PENDING = "pending"
    STATUS_VALID = "valid"
    STATUS_INVALID = "invalid"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_APPLIED = "applied"
    STATUS_CHOICES = [(value, value.title()) for value in (
        STATUS_PENDING, STATUS_VALID, STATUS_INVALID, STATUS_APPROVED, STATUS_REJECTED, STATUS_APPLIED,
    )]

    batch = models.ForeignKey(CatalogEnrichmentBatch, on_delete=models.PROTECT, related_name="proposals")
    catalog_food = models.ForeignKey(CatalogFood, on_delete=models.PROTECT, related_name="enrichment_proposals")
    field_name = models.CharField(max_length=120)
    capability_definition = models.ForeignKey(
        CatalogCapabilityDefinition, on_delete=models.PROTECT, null=True, blank=True, related_name="proposals"
    )
    expected_food_updated_at = models.DateTimeField()
    current_value = models.JSONField(null=True, blank=True)
    proposed_value = models.JSONField(null=True, blank=True)
    nature = models.CharField(max_length=40, choices=CatalogCapabilityDefinition.NATURE_CHOICES)
    provenance = models.JSONField(default=list)
    consumers = models.JSONField(default=list)
    maturity = models.CharField(max_length=30, choices=CatalogCapabilityDefinition.MATURITY_CHOICES)
    generation_method = models.CharField(max_length=40, default="codex_assisted")
    authority_requirement = models.CharField(max_length=40, choices=CatalogCapabilityDefinition.AUTHORITY_CHOICES)
    risk_level = models.CharField(max_length=20, choices=CatalogCapabilityDefinition.RISK_CHOICES)
    assessment_status = models.CharField(max_length=40, choices=CatalogFoodCapability.STATUS_CHOICES)
    profile_key = models.CharField(max_length=100, blank=True)
    policy_version = models.CharField(max_length=80, blank=True)
    rationale = models.TextField()
    confidence = models.DecimalField(max_digits=5, decimal_places=2)
    evidence_references = models.JSONField(default=list, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_catalog_field_proposals"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["batch", "catalog_food", "field_name"], name="unique_catalog_batch_food_field")
        ]
        ordering = ["batch", "catalog_food", "field_name"]


class CatalogEnrichmentChange(models.Model):
    """Append-only ledger entry for an applied or compensating enrichment change."""

    ACTION_APPLY = "apply"
    ACTION_REVERT = "revert"
    ACTION_CHOICES = [(ACTION_APPLY, "Apply"), (ACTION_REVERT, "Revert")]

    batch = models.ForeignKey(CatalogEnrichmentBatch, on_delete=models.PROTECT, related_name="changes")
    proposal = models.ForeignKey(CatalogFieldProposal, on_delete=models.PROTECT, related_name="changes")
    catalog_food = models.ForeignKey(CatalogFood, on_delete=models.PROTECT, related_name="enrichment_changes")
    field_name = models.CharField(max_length=120)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    value_before = models.JSONField(null=True, blank=True)
    value_after = models.JSONField(null=True, blank=True)
    food_updated_at_before = models.DateTimeField()
    food_updated_at_after = models.DateTimeField()
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="catalog_enrichment_changes"
    )
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk and CatalogEnrichmentChange.objects.filter(pk=self.pk).exists():
            from django.core.exceptions import ValidationError
            raise ValidationError("CatalogEnrichmentChange entries are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        raise ValidationError("CatalogEnrichmentChange entries are append-only.")
