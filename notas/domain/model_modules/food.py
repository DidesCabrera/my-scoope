from django.contrib.auth.models import User
from django.db import models

from notas.domain.constants.nutrition import (
    CARBS_KCAL_PER_GRAM,
    FAT_KCAL_PER_GRAM,
    PROTEIN_KCAL_PER_GRAM,
)

# ==================================================
# FOOD
# ==================================================

class Food(models.Model):
    CATALOG_SYNC_NONE = "none"
    CATALOG_SYNC_SNAPSHOT = "snapshot"
    CATALOG_SYNC_STALE = "stale"
    CATALOG_SYNC_UNLINKED = "unlinked"

    CATALOG_SYNC_CHOICES = [
        (CATALOG_SYNC_NONE, "None"),
        (CATALOG_SYNC_SNAPSHOT, "Snapshot"),
        (CATALOG_SYNC_STALE, "Stale"),
        (CATALOG_SYNC_UNLINKED, "Unlinked"),
    ]

    VISIBILITY_CORE = "core"
    VISIBILITY_EXTENDED = "extended"
    VISIBILITY_HIDDEN = "hidden"
    VISIBILITY_REJECTED = "rejected"

    VISIBILITY_CHOICES = [
        (VISIBILITY_CORE, "Core"),
        (VISIBILITY_EXTENDED, "Extended"),
        (VISIBILITY_HIDDEN, "Hidden"),
        (VISIBILITY_REJECTED, "Rejected"),
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

    name = models.CharField(max_length=100)

    protein = models.FloatField()
    carbs = models.FloatField()
    fat = models.FloatField()

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
    )

    is_global = models.BooleanField(
        default=False,
        help_text="If true, this food is available to every user as part of the global catalog.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    list_order = models.PositiveIntegerField(default=0)

    canonical_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Normalized name for search, deduplication and external sources.",
    )

    is_verified = models.BooleanField(
        default=False,
        help_text="Indicates whether this food has been reviewed or approved for reliable use.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Allows hiding foods without deleting them.",
    )

    food_group = models.CharField(
        max_length=120,
        blank=True,
        help_text="General nutritional/category group. Example: cereals, meats, legumes.",
    )

    food_subgroup = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional nutritional/category subgroup.",
    )

    preparation_state = models.CharField(
        max_length=30,
        choices=PREPARATION_STATE_CHOICES,
        default=PREPARATION_UNKNOWN,
        help_text=(
            "Copied semantic state from Food Catalog when available. Used to avoid "
            "mixing raw/cooked/dry/hydrated foods in future optimization flows."
        ),
    )

    solver_enabled = models.BooleanField(
        default=False,
        help_text="Whether this operational food may be used by future nutrition solver candidates.",
    )

    solver_capabilities_version = models.CharField(
        max_length=64,
        default="solver_food_capabilities.v1",
        help_text="Version of the solver capability projection copied into this operational snapshot.",
    )

    solver_capabilities = models.JSONField(
        default=dict,
        blank=True,
        help_text="Operational, auditable capability values and confidence; never a live CatalogFood read.",
    )

    fiber_g_per_100g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Fiber in grams per 100 g.",
    )

    sugar_g_per_100g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Sugar in grams per 100 g.",
    )

    saturated_fat_g_per_100g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Saturated fat in grams per 100 g.",
    )

    sodium_mg_per_100g = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Sodium in milligrams per 100 g.",
    )

    default_portion_g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Suggested default portion in grams.",
    )

    min_portion_g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Suggested minimum portion for future optimization.",
    )

    max_portion_g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Suggested maximum portion for future optimization.",
    )

    portion_step_g = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Suggested portion increment step.",
    )

    data_quality_score = models.PositiveSmallIntegerField(
        default=0,
        help_text="Internal data quality score from 0 to 100.",
    )

    visibility = models.CharField(
        max_length=30,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_EXTENDED,
        help_text="Food visibility level in search and catalogs.",
    )

    catalog_food_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Optional trace to food_catalog.CatalogFood. This is not a ForeignKey "
            "and is never an operational food ID for Meals, Solver or MCP."
        ),
    )

    catalog_food_ref = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Stable Food Catalog reference copied when this Food is created/refreshed from a catalog snapshot.",
    )

    catalog_snapshot_version = models.CharField(
        max_length=64,
        blank=True,
        help_text="Food Catalog version label used to create or refresh this operational snapshot.",
    )

    catalog_snapshot_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Auditable payload copied from Food Catalog at snapshot time.",
    )

    catalog_snapshot_created_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date/time when the Food Catalog snapshot was materialized into notas.Food.",
    )

    catalog_sync_status = models.CharField(
        max_length=24,
        choices=CATALOG_SYNC_CHOICES,
        default=CATALOG_SYNC_NONE,
        help_text="Internal sync state for the optional Food Catalog trace.",
    )

    def __str__(self):
        return self.name

    # ---- kcal por macro (por 100g) ----
    @property
    def kcal_protein(self):
        return self.protein * PROTEIN_KCAL_PER_GRAM

    @property
    def kcal_carbs(self):
        return self.carbs * CARBS_KCAL_PER_GRAM

    @property
    def kcal_fat(self):
        return self.fat * FAT_KCAL_PER_GRAM

    @property
    def total_kcal(self):
        return self.kcal_protein + self.kcal_carbs + self.kcal_fat

    # ---- alloc por food ----
    @property
    def alloc(self):
        if self.total_kcal == 0:
            return {"protein": 0, "carbs": 0, "fat": 0}

        return {
            "protein": self.kcal_protein / self.total_kcal * 100,
            "carbs": self.kcal_carbs / self.total_kcal * 100,
            "fat": self.kcal_fat / self.total_kcal * 100,
        }

    @property
    def category(self):
        """
        Logical UI/read category.

        Keep this property stable because it is used by queries,
        DTOs, presentation builders and tests.
        """
        if self.is_global or self.created_by_id is None:
            return "system"

        return "user"


class FoodSourceMetadata(models.Model):
    SOURCE_MANUAL = "manual"
    SOURCE_USDA = "usda"
    SOURCE_OPEN_FOOD_FACTS = "open_food_facts"
    SOURCE_LATINFOODS = "latinfoods"
    SOURCE_INTA_CHILE = "inta_chile"
    SOURCE_ADMIN_IMPORT = "admin_import"

    SOURCE_CHOICES = [
        (SOURCE_MANUAL, "Manual"),
        (SOURCE_USDA, "USDA FoodData Central"),
        (SOURCE_OPEN_FOOD_FACTS, "Open Food Facts"),
        (SOURCE_LATINFOODS, "LATINFOODS"),
        (SOURCE_INTA_CHILE, "INTA Chile"),
        (SOURCE_ADMIN_IMPORT, "Admin import"),
    ]

    food = models.OneToOneField(
        Food,
        on_delete=models.CASCADE,
        related_name="source_metadata",
    )

    source = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
    )

    source_food_id = models.CharField(
        max_length=120,
        blank=True,
        help_text="Food ID in the external source.",
    )

    source_dataset = models.CharField(
        max_length=120,
        blank=True,
        help_text="Specific dataset inside the source.",
    )

    source_version = models.CharField(
        max_length=120,
        blank=True,
        help_text="Source dataset version.",
    )

    source_url = models.URLField(
        blank=True,
        help_text="Reference URL for the original source.",
    )

    imported_at = models.DateTimeField(auto_now_add=True)

    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last date this food was compared or synchronized with its source.",
    )

    raw_payload_hash = models.CharField(
        max_length=128,
        blank=True,
        help_text="Hash of the original imported payload.",
    )

    normalized_payload_hash = models.CharField(
        max_length=128,
        blank=True,
        help_text="Hash of the normalized payload used by My Scoope.",
    )

    license_name = models.CharField(
        max_length=120,
        blank=True,
    )

    attribution = models.TextField(
        blank=True,
    )

    class Meta:
        verbose_name = "Food source metadata"
        verbose_name_plural = "Food source metadata"

        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_food_id"],
                condition=~models.Q(source_food_id=""),
                name="unique_food_source_external_id",
            )
        ]

    def __str__(self):
        return f"{self.food} · {self.source}"


class FoodLabelCaptureReceipt(models.Model):
    BASIS_PER_100G = "per_100g"
    BASIS_PER_SERVING = "per_serving"
    BASIS_MANUAL = "manual"
    BASIS_CHOICES = [
        (BASIS_PER_100G, "Per 100 g"),
        (BASIS_PER_SERVING, "Per serving"),
        (BASIS_MANUAL, "Manual review"),
    ]

    food = models.OneToOneField(
        Food,
        on_delete=models.CASCADE,
        related_name="label_capture_receipt",
    )
    idempotency_key = models.CharField(max_length=120, unique=True)
    ocr_engine = models.CharField(max_length=80)
    ocr_engine_version = models.CharField(max_length=40, blank=True)
    detected_basis = models.CharField(max_length=24, choices=BASIS_CHOICES)
    serving_size_g = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    declared_energy_kcal_per_100g = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    field_confidence = models.JSONField(default=dict, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    confirmed_payload_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["ocr_engine", "created_at"],
                name="food_label_ocr_engine_idx",
            ),
        ]

    def __str__(self):
        return f"{self.food} · {self.ocr_engine}"


class FoodPortion(models.Model):
    food = models.ForeignKey(
        Food,
        on_delete=models.CASCADE,
        related_name="portions",
    )

    label = models.CharField(
        max_length=120,
        help_text="Portion name. Example: 1 large egg, 1 cup, 1 tablespoon.",
    )

    grams = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        help_text="Portion equivalent in grams.",
    )

    source = models.CharField(
        max_length=50,
        blank=True,
        help_text="Portion source: manual, usda, open_food_facts, etc.",
    )

    is_default = models.BooleanField(
        default=False,
    )

    class Meta:
        verbose_name = "Food portion"
        verbose_name_plural = "Food portions"
        ordering = ["food", "-is_default", "label"]

    def __str__(self):
        return f"{self.food} · {self.label} = {self.grams} g"


class FoodAlias(models.Model):
    food = models.ForeignKey(
        Food,
        on_delete=models.CASCADE,
        related_name="aliases",
    )

    name = models.CharField(
        max_length=255,
        help_text="Alternative food name or search alias.",
    )

    normalized_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Normalized alias for search.",
    )

    language = models.CharField(
        max_length=10,
        default="es",
    )

    country = models.CharField(
        max_length=10,
        blank=True,
        help_text="Optional country code. Example: CL, AR, MX.",
    )

    class Meta:
        verbose_name = "Food alias"
        verbose_name_plural = "Food aliases"
        ordering = ["food", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["food", "normalized_name", "language", "country"],
                condition=~models.Q(normalized_name=""),
                name="unique_food_alias_per_language_country",
            )
        ]

    def __str__(self):
        return f"{self.name} → {self.food}"


class FoodLocalizedName(models.Model):
    food = models.ForeignKey(
        Food,
        on_delete=models.CASCADE,
        related_name="localized_names",
    )

    name = models.CharField(
        max_length=255,
        help_text="Localized display name for this food.",
    )

    normalized_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Normalized localized name for search and deduplication.",
    )

    language = models.CharField(
        max_length=10,
        default="es",
    )

    country = models.CharField(
        max_length=10,
        blank=True,
        help_text="Optional country code. Example: CL, AR, MX.",
    )

    is_primary = models.BooleanField(
        default=True,
        help_text="Primary localized name for this language/country.",
    )

    class Meta:
        verbose_name = "Food localized name"
        verbose_name_plural = "Food localized names"
        ordering = [
            "food",
            "language",
            "country",
            "-is_primary",
            "name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["food", "normalized_name", "language", "country"],
                condition=~models.Q(normalized_name=""),
                name="unique_food_localized_name_per_language_country",
            )
        ]

    def __str__(self):
        return f"{self.name} → {self.food}"


class FoodImportBatch(models.Model):
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

    source = models.CharField(
        max_length=50,
        help_text="Imported source. Example: usda, open_food_facts, latinfoods.",
    )

    source_version = models.CharField(
        max_length=120,
        blank=True,
    )

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    total_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)
    skipped_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    class Meta:
        verbose_name = "Food import batch"
        verbose_name_plural = "Food import batches"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.source} · {self.source_version or 'sin versión'} · {self.status}"
