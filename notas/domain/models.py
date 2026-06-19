from django.db import models
from django.db.models import Prefetch
from django.contrib.auth.models import User
from notas.domain.constants.nutrition import (
    PROTEIN_KCAL_PER_GRAM,
    CARBS_KCAL_PER_GRAM,
    FAT_KCAL_PER_GRAM,
)
import uuid
from notas.domain.services.nutrition import compute_meal_nutrition



# ==================================================
# PLANS / PROFILES / SUBSCRIPTIONS
# ==================================================

class Plan(models.Model):
    ROLE_CHOICES = (
        ("member", "Member"),
        ("nutritionist", "Nutritionist"),
    )

    name = models.CharField(max_length=50)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    can_create_meal = models.BooleanField(default=False)
    can_create_dailyplan = models.BooleanField(default=False)
    can_create_program = models.BooleanField(default=False)
    can_publish = models.BooleanField(default=False)

    can_fork = models.BooleanField(default=True)
    can_copy = models.BooleanField(default=False)



    max_program_duration_days = models.PositiveIntegerField(null=True, blank=True)
    max_active_subscriptions = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.role})"


class Profile(models.Model):
    ROLE_CHOICES = (
        ("member", "Member"),
        ("nutritionist", "Nutritionist"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    plan = models.ForeignKey(Plan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles")
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Subscription(models.Model):
    nutritionist = models.ForeignKey(
        User, related_name="subscriptions_received", on_delete=models.CASCADE
    )
    member = models.ForeignKey(
        User, related_name="subscriptions_made", on_delete=models.CASCADE
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("nutritionist", "member")

    def __str__(self):
        return f"{self.member} → {self.nutritionist}"


class MCPUserToken(models.Model):
    user = models.ForeignKey(
        User,
        related_name="mcp_user_tokens",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=120)
    token_hash = models.CharField(
        max_length=64,
        unique=True,
    )
    scopes = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [
            "-created_at",
            "-id",
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    @property
    def is_revoked(self):
        return self.revoked_at is not None

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


class OAuthClient(models.Model):
    client_id = models.CharField(
        max_length=120,
        unique=True,
    )
    client_name = models.CharField(max_length=160)
    redirect_uris = models.JSONField(default=list)
    allowed_scopes = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "client_name",
            "id",
        ]

    def __str__(self):
        return self.client_name

    def allows_redirect_uri(self, redirect_uri: str) -> bool:
        return redirect_uri in self.redirect_uris

    def allows_scope(self, scope: str) -> bool:
        return scope in self.allowed_scopes

    def allows_scopes(self, scopes: list[str]) -> bool:
        return all(
            self.allows_scope(scope)
            for scope in scopes
        )


class OAuthAuthorizationCode(models.Model):
    client = models.ForeignKey(
        OAuthClient,
        related_name="authorization_codes",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        User,
        related_name="oauth_authorization_codes",
        on_delete=models.CASCADE,
    )
    code_hash = models.CharField(
        max_length=64,
        unique=True,
    )
    redirect_uri = models.URLField(max_length=500)
    scopes = models.JSONField(default=list)
    code_challenge = models.CharField(max_length=160)
    code_challenge_method = models.CharField(max_length=20)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [
            "-created_at",
            "-id",
        ]

    def __str__(self):
        return f"OAuth code for {self.user.username} / {self.client.client_id}"

    @property
    def is_used(self):
        return self.used_at is not None


# ==================================================
# FOOD
# ==================================================

class Food(models.Model):
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



# ==================================================
# MEAL + MEAL FOOD
# ==================================================

class Meal(models.Model):
    name = models.CharField(max_length=100)

    foods = models.ManyToManyField(Food, through="MealFood")

    is_public = models.BooleanField(default=False)
    is_forkable = models.BooleanField(default=True)
    is_copiable = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=True)
    
    pending_dailyplan = models.ForeignKey(
        "DailyPlan",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+"
    )

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    original_author = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    forked_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="variants"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    list_order = models.PositiveIntegerField(default=0)

    def kind(self):
        return "Meal"

    def __str__(self):
        return self.name

    # ==================================================
    # DOMAIN STATE HELPERS
    # ==================================================

    @property
    def is_dpm_instance(self):
        """Meal que vive dentro de un DailyPlanMeal."""
        annotated_value = getattr(self, "is_dpm_instance_sql", None)

        if annotated_value is not None:
            return bool(annotated_value)

        cached_value = getattr(self, "_is_dpm_instance", None)

        if cached_value is not None:
            return bool(cached_value)

        return self.dailyplanmeal_set.exists()


    @property
    def is_original(self):
        """Meal creada desde cero por el usuario."""
        return (
            self.forked_from is None
            and not self.is_dpm_instance
        )

    @property
    def is_duplicate(self):
        """Meal copiada desde otra meal pero guardada en la biblioteca."""
        return (
            self.forked_from is not None
            and not self.is_dpm_instance
        )

    @property
    def category(self):
        """
        Categoría lógica de la meal.
        """
        if self.is_dpm_instance:
            return "en plan"

        if self.forked_from:
            return "duplicada"

        return "original"

    # ---- gramos ----

    @property
    def protein(self):
        if self.protein_cached is not None:
            return self.protein_cached
        return compute_meal_nutrition(self)["protein"]

    @property
    def carbs(self):
        if self.carbs_cached is not None:
            return self.carbs_cached
        return compute_meal_nutrition(self)["carbs"]

    @property
    def fat(self):
        if self.fat_cached is not None:
            return self.fat_cached
        return compute_meal_nutrition(self)["fat"]


    # ---- kcal ----
    @property
    def kcal_protein(self):
        return sum(mf.kcal_protein for mf in self.meal_food_set.all())

    @property
    def kcal_carbs(self):
        return sum(mf.kcal_carbs for mf in self.meal_food_set.all())

    @property
    def kcal_fat(self):
        return sum(mf.kcal_fat for mf in self.meal_food_set.all())

    @property
    def total_kcal(self):
        return self.kcal_protein + self.kcal_carbs + self.kcal_fat

    @property
    def alloc(self):
        if self.total_kcal == 0:
            return {"protein": 0, "carbs": 0, "fat": 0}

        return {
            "protein": self.kcal_protein / self.total_kcal * 100,
            "carbs": self.kcal_carbs / self.total_kcal * 100,
            "fat": self.kcal_fat / self.total_kcal * 100,
        }

    # ==================================================
    # CACHED
    # ==================================================

    protein_cached = models.FloatField(null=True, blank=True)
    carbs_cached = models.FloatField(null=True, blank=True)
    fat_cached = models.FloatField(null=True, blank=True)

    kcal_protein_cached = models.FloatField(null=True, blank=True)
    kcal_carbs_cached = models.FloatField(null=True, blank=True)
    kcal_fat_cached = models.FloatField(null=True, blank=True)
    total_kcal_cached = models.FloatField(null=True, blank=True)

    alloc_protein_cached = models.FloatField(null=True, blank=True)
    alloc_carbs_cached = models.FloatField(null=True, blank=True)
    alloc_fat_cached = models.FloatField(null=True, blank=True)

    foods_aggregation_cached = models.JSONField(null=True, blank=True)



    # ==================================================
    # DOMAIN API (delegates to services)
    # ==================================================

    def update_draft_status(self):
        if self.meal_food_set.exists():
            if self.is_draft:
                self.is_draft = False
                self.save(update_fields=["is_draft"])



class MealFood(models.Model):
    meal = models.ForeignKey(
        Meal,
        on_delete=models.CASCADE,
        related_name="meal_food_set")
    
    food = models.ForeignKey(
        Food, 
        on_delete=models.CASCADE)

    quantity = models.FloatField(help_text="grams")

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.food} in {self.meal}"

    @property
    def factor(self):
        return self.quantity / 100

    @property
    def protein(self):
        return self.food.protein * self.factor

    @property
    def carbs(self):
        return self.food.carbs * self.factor

    @property
    def fat(self):
        return self.food.fat * self.factor

    @property
    def kcal_protein(self):
        return self.food.kcal_protein * self.factor

    @property
    def kcal_carbs(self):
        return self.food.kcal_carbs * self.factor

    @property
    def kcal_fat(self):
        return self.food.kcal_fat * self.factor

    @property
    def total_kcal(self):
        return self.kcal_protein + self.kcal_carbs + self.kcal_fat


    # ---------- alloc por macro dentro de la meal ----------

    @property
    def alloc_protein(self):
        total = self.meal.kcal_protein
        if total == 0:
            return 0
        return self.kcal_protein / total * 100

    @property
    def alloc_carbs(self):
        total = self.meal.kcal_carbs
        if total == 0:
            return 0
        return self.kcal_carbs / total * 100

    @property
    def alloc_fat(self):
        total = self.meal.kcal_fat
        if total == 0:
            return 0
        return self.kcal_fat / total * 100

    @property
    def alloc(self):
        return {
            "protein": self.alloc_protein,
            "carbs": self.alloc_carbs,
            "fat": self.alloc_fat,
        }

    @property
    def kcal_share(self):
        total = self.meal.total_kcal
        if not total or total <= 0:
            return 0.0
        return self.total_kcal / total * 100

    


# ==================================================
# DAILY PLAN + PROGRAM
# ==================================================

class DailyPlan(models.Model):
    SOURCE_MANUAL = "manual"
    SOURCE_AI = "ai"
    SOURCE_SYSTEM = "system"
    SOURCE_MCP = "mcp"
    SOURCE_PROGRAM = "program"

    SOURCE_CHOICES = (
        (SOURCE_MANUAL, "Manual"),
        (SOURCE_AI, "AI"),
        (SOURCE_SYSTEM, "System"),
        (SOURCE_MCP, "MCP"),
        (SOURCE_PROGRAM, "Program"),
    )
    name = models.CharField(max_length=100)
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    original_author = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    forked_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="variants"
    )

    is_public = models.BooleanField(default=False)
    is_forkable = models.BooleanField(default=True)
    is_copiable = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    list_order = models.PositiveIntegerField(default=0)

    def kind(self):
        return "Daily Plan"

    def __str__(self):
        return self.name

    # ==================================================
    # DOMAIN STATE HELPERS
    # ==================================================

    @property
    def is_original(self):
        """
        DailyPlan creado desde cero por el usuario.
        """
        return self.forked_from is None


    @property
    def is_duplicate(self):
        """
        DailyPlan fork/copied desde otro plan.
        """
        return self.forked_from is not None


    @property
    def is_program_instance(self):
        """Snapshot interno usado dentro de un Programa Semanal."""
        return self.source == self.SOURCE_PROGRAM


    @property
    def category(self):
        """Categoría lógica del DailyPlan."""
        if self.is_program_instance:
            return "en programa"

        if self.forked_from:
            return "duplicado"

        return "original"


    @property
    def protein(self):
        return sum(dpm.meal.protein for dpm in self.dailyplan_meals.all())

    @property
    def carbs(self):
        return sum(dpm.meal.carbs for dpm in self.dailyplan_meals.all())

    @property
    def fat(self):
        return sum(dpm.meal.fat for dpm in self.dailyplan_meals.all())

    @property
    def kcal_protein(self):
        return sum(dpm.meal.kcal_protein for dpm in self.dailyplan_meals.all())

    @property
    def kcal_carbs(self):
        return sum(dpm.meal.kcal_carbs for dpm in self.dailyplan_meals.all())

    @property
    def kcal_fat(self):
        return sum(dpm.meal.kcal_fat for dpm in self.dailyplan_meals.all())

    @property
    def total_kcal(self):
        return self.kcal_protein + self.kcal_carbs + self.kcal_fat

    @property
    def alloc(self):
        if self.total_kcal == 0:
            return {"protein": 0, "carbs": 0, "fat": 0}

        return {
            "protein": self.kcal_protein / self.total_kcal * 100,
            "carbs": self.kcal_carbs / self.total_kcal * 100,
            "fat": self.kcal_fat / self.total_kcal * 100,
        }
    
    def meals_with_foods(self):
        return (
            self.dailyplan_meals
            .select_related("meal")
            .prefetch_related(
                Prefetch(
                    "meal__meal_food_set",
                    queryset=MealFood.objects.select_related("food")
                )
            )
        )
    
    # ==================================================
    # DOMAIN API (delegates to services)
    # ==================================================

    def update_draft_status(self):

        if not self.is_draft:
            return

        if self.dailyplan_meals.exists():
            self.is_draft = False
            self.save(update_fields=["is_draft"])


class DailyPlanMeal(models.Model):
    dailyplan = models.ForeignKey(
        DailyPlan,
        on_delete=models.CASCADE,
        related_name="dailyplan_meals"
    )
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)

    note = models.CharField(max_length=255, blank=True, null=True)
    hour = models.TimeField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.dailyplan.name} ({self.meal.name})"

    # ------------------
    # Totales
    # ------------------

    @property
    def total_kcal(self):
        return (
            self.meal.kcal_protein +
            self.meal.kcal_carbs +
            self.meal.kcal_fat
        )

    # ------------------
    # Alloc relativo (%)
    # ------------------

    def _safe_alloc(self, part, total):
        if not total or total <= 0:
            return 0.0
        return (part / total) * 100

    @property
    def alloc_protein(self):
        return self._safe_alloc(
            self.meal.kcal_protein,
            self.dailyplan.kcal_protein
        )

    @property
    def alloc_carbs(self):
        return self._safe_alloc(
            self.meal.kcal_carbs,
            self.dailyplan.kcal_carbs
        )

    @property
    def alloc_fat(self):
        return self._safe_alloc(
            self.meal.kcal_fat,
            self.dailyplan.kcal_fat
        )

    @property
    def alloc(self):
        return {
            "protein": self.alloc_protein,
            "carbs": self.alloc_carbs,
            "fat": self.alloc_fat,
        }

    @property
    def kcal_share(self):
        total = self.dailyplan.total_kcal
        if not total or total <= 0:
            return 0.0
        return self.total_kcal / total * 100



# ==================================================
# NUTRITION PROPOSALS
# ==================================================

class NutritionProposal(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PENDING_REVIEW = "pending_review"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CANCELLED = "cancelled"
    STATUS_APPLIED = "applied"

    STATUS_CHOICES = (
        (STATUS_PENDING_REVIEW, "Pendiente"),
        (STATUS_REJECTED, "Rechazada"),
        (STATUS_APPLIED, "Aplicada"),
    )

    SOURCE_MANUAL = "manual"
    SOURCE_AI = "ai"
    SOURCE_SYSTEM = "system"
    SOURCE_MCP = "mcp"

    SOURCE_CHOICES = (
        (SOURCE_MANUAL, "Manual"),
        (SOURCE_AI, "AI"),
        (SOURCE_SYSTEM, "System"),
        (SOURCE_MCP, "MCP"),
    )

    dailyplan = models.ForeignKey(
        DailyPlan,
        on_delete=models.CASCADE,
        related_name="nutrition_proposals",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="nutrition_proposals_created",
    )

    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="nutrition_proposals_reviewed",
    )

    applied_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="nutrition_proposals_applied",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING_REVIEW,
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
    )

    title = models.CharField(max_length=160)
    summary = models.TextField(blank=True)
    list_order = models.PositiveIntegerField(default=0)
    is_read = models.BooleanField(default=False)

    targets = models.JSONField(default=dict, blank=True)
    current_snapshot = models.JSONField(default=dict, blank=True)
    proposed_payload = models.JSONField(default=dict, blank=True)
    validation_summary = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.title} ({self.status})"

    @property
    def is_reviewable(self):
        return self.status == self.STATUS_PENDING_REVIEW

    @property
    def is_final(self):
        return self.status in {
            self.STATUS_REJECTED,
            self.STATUS_APPLIED,
        }



class NutritionProposalAuditEvent(models.Model):
    ACTION_CREATED = "created"
    ACTION_SUBMITTED_FOR_REVIEW = "submitted_for_review"
    ACTION_APPROVED = "approved"
    ACTION_REJECTED = "rejected"
    ACTION_CANCELLED = "cancelled"
    ACTION_APPLIED = "applied"

    ACTION_CHOICES = (
        (ACTION_CREATED, "Created"),
        (ACTION_SUBMITTED_FOR_REVIEW, "Submitted for review"),
        (ACTION_APPROVED, "Approved"),
        (ACTION_REJECTED, "Rejected"),
        (ACTION_CANCELLED, "Cancelled"),
        (ACTION_APPLIED, "Applied"),
    )

    proposal = models.ForeignKey(
        NutritionProposal,
        on_delete=models.CASCADE,
        related_name="audit_events",
    )

    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="nutrition_proposal_audit_events",
    )

    action = models.CharField(
        max_length=40,
        choices=ACTION_CHOICES,
    )

    status_before = models.CharField(
        max_length=30,
        blank=True,
    )

    status_after = models.CharField(
        max_length=30,
        blank=True,
    )

    message = models.TextField(blank=True)

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.proposal_id} - {self.action}"
    





class Program(models.Model):
    MIN_DURATION_WEEKS = 1
    DEFAULT_DURATION_WEEKS = 1

    name = models.CharField(max_length=100)

    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="programs"
    )
    original_author = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    forked_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="variants"
    )

    # Legacy calendar fields. Weekly programs are now duration-based and do not
    # depend on a concrete calendar start/end date.
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    duration_weeks = models.PositiveSmallIntegerField(default=DEFAULT_DURATION_WEEKS)

    is_public = models.BooleanField(default=False)
    is_forkable = models.BooleanField(default=True)
    is_copiable = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    list_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["list_order", "-created_at", "-id"]

    def kind(self):
        return "Program"

    def __str__(self):
        return self.name

    @property
    def normalized_duration_weeks(self):
        return max(self.duration_weeks or self.DEFAULT_DURATION_WEEKS, self.MIN_DURATION_WEEKS)

    @property
    def duration_days(self):
        return self.normalized_duration_weeks * 7

    @property
    def filled_days_count(self):
        return self.program_dailyplan.count()

    @property
    def empty_days_count(self):
        return max(self.duration_days - self.filled_days_count, 0)

    @property
    def protein(self):
        return sum(day.dailyplan.protein for day in self.program_dailyplan.all())

    @property
    def carbs(self):
        return sum(day.dailyplan.carbs for day in self.program_dailyplan.all())

    @property
    def fat(self):
        return sum(day.dailyplan.fat for day in self.program_dailyplan.all())

    @property
    def total_protein_g(self):
        return self.protein

    @property
    def total_carbs_g(self):
        return self.carbs

    @property
    def total_fat_g(self):
        return self.fat

    @property
    def kcal_protein(self):
        return sum(day.dailyplan.kcal_protein for day in self.program_dailyplan.all())

    @property
    def kcal_carbs(self):
        return sum(day.dailyplan.kcal_carbs for day in self.program_dailyplan.all())

    @property
    def kcal_fat(self):
        return sum(day.dailyplan.kcal_fat for day in self.program_dailyplan.all())

    @property
    def total_kcal(self):
        return self.kcal_protein + self.kcal_carbs + self.kcal_fat

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
    def average_weekly_kcal(self):
        if not self.normalized_duration_weeks:
            return 0
        return self.total_kcal / self.normalized_duration_weeks


class ProgramDay(models.Model):
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="program_dailyplan"
    )
    dailyplan = models.ForeignKey(
        DailyPlan,
        on_delete=models.CASCADE,
        related_name="program_slots",
    )
    # Legacy date field kept nullable for old rows / migrations.
    date = models.DateField(null=True, blank=True)
    week_number = models.PositiveSmallIntegerField(default=1)
    day_number = models.PositiveSmallIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["week_number", "day_number", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["program", "week_number", "day_number"],
                name="unique_program_week_day",
            )
        ]

    def __str__(self):
        return f"{self.program.name} - Semana {self.week_number}, día {self.day_number}"

    @property
    def slot_label(self):
        return f"S{self.week_number} · D{self.day_number}"


# ==================================================
# ACCESS
# ==================================================

class MealAccess(models.Model):
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    granted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)


# ==================================================
# WEIGHT TRACKING (PROGRESS)
# ==================================================


class WeightLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="weight_logs"
    )

    date = models.DateField()
    weight_kg = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        unique_together = ("user", "date")   # opcional: un registro por día

    def __str__(self):
        return f"{self.user.username} - {self.weight_kg} kg ({self.date})"




class DailyPlanShare(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="dailyplan_shares_sent"
    )

    recipient_email = models.EmailField()

    dailyplan = models.ForeignKey(
        DailyPlan,
        on_delete=models.CASCADE,
        related_name="shares"
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True)

    accepted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dailyplan_shares_received"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    
    dismissed = models.BooleanField(default=False)      # inbox
    removed = models.BooleanField(default=False)        # librería
    is_favorite = models.BooleanField(default=False)    # inbox
    is_read = models.BooleanField(default=False)        # inbox
    message = models.TextField(blank=True)              # inbox / email
    subject = models.CharField(max_length=160, blank=True)  # inbox title / email subject

    class Meta:
        unique_together = ("recipient_email", "dailyplan")

    def __str__(self):
        return f"{self.sender} shared {self.dailyplan} → {self.recipient_email}"


class ProgramShare(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="program_shares_sent"
    )

    recipient_email = models.EmailField()

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="shares"
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True)

    accepted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="program_shares_received"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    dismissed = models.BooleanField(default=False)
    removed = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    message = models.TextField(blank=True)
    subject = models.CharField(max_length=160, blank=True)

    class Meta:
        unique_together = ("recipient_email", "program")

    def __str__(self):
        return f"{self.sender} shared {self.program} → {self.recipient_email}"


class MealShare(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="meal_shares_sent"
    )

    recipient_email = models.EmailField()

    meal = models.ForeignKey(
        Meal,
        on_delete=models.CASCADE,
        related_name="shares"
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True)

    accepted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="meal_shares_received"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    
    dismissed = models.BooleanField(default=False)      # inbox
    removed = models.BooleanField(default=False)        # librería
    is_favorite = models.BooleanField(default=False)    # inbox
    is_read = models.BooleanField(default=False)        # inbox
    message = models.TextField(blank=True)              # inbox / email
    subject = models.CharField(max_length=160, blank=True)  # inbox title / email subject

    class Meta:
        unique_together = ("recipient_email", "meal")

    def __str__(self):
        return f"{self.sender} shared {self.meal} → {self.recipient_email}"

class FoodShare(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="food_shares_sent"
    )

    recipient_email = models.EmailField()

    food = models.ForeignKey(
        Food,
        on_delete=models.CASCADE,
        related_name="shares"
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True)

    accepted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="food_shares_received"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    dismissed = models.BooleanField(default=False)
    removed = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    message = models.TextField(blank=True)
    subject = models.CharField(max_length=160, blank=True)

    class Meta:
        unique_together = ("recipient_email", "food")

    def __str__(self):
        return f"{self.sender} shared {self.food} → {self.recipient_email}"


class DailyPlanMealShare(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="dailyplanmeal_shares_sent"
    )

    recipient_email = models.EmailField()

    dailyplan_meal = models.ForeignKey(
        DailyPlanMeal,
        on_delete=models.CASCADE,
        related_name="shares"
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True)

    accepted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dailyplanmeal_shares_received"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    dismissed = models.BooleanField(default=False)
    removed = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    message = models.TextField(blank=True)
    subject = models.CharField(max_length=160, blank=True)

    class Meta:
        unique_together = ("recipient_email", "dailyplan_meal")

    def __str__(self):
        return f"{self.sender} shared {self.dailyplan_meal} → {self.recipient_email}"
