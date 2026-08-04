from django.contrib.auth.models import User
from django.db import models
from django.db.models import Prefetch

from notas.domain.model_modules.meals import Meal, MealFood

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

    summary_cache = models.JSONField(default=dict, blank=True)
    summary_cache_updated_at = models.DateTimeField(null=True, blank=True)

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


    def _summary_metric(self, key):
        cached = (self.summary_cache or {}).get("totals", {}).get(key)
        if cached is not None:
            return cached
        return None

    @property
    def protein(self):
        cached = self._summary_metric("protein")
        if cached is not None:
            return cached
        return sum(dpm.meal.protein for dpm in self.dailyplan_meals.all())

    @property
    def carbs(self):
        cached = self._summary_metric("carbs")
        if cached is not None:
            return cached
        return sum(dpm.meal.carbs for dpm in self.dailyplan_meals.all())

    @property
    def fat(self):
        cached = self._summary_metric("fat")
        if cached is not None:
            return cached
        return sum(dpm.meal.fat for dpm in self.dailyplan_meals.all())

    @property
    def kcal_protein(self):
        cached = self._summary_metric("kcal_protein")
        if cached is not None:
            return cached
        return sum(dpm.meal.kcal_protein for dpm in self.dailyplan_meals.all())

    @property
    def kcal_carbs(self):
        cached = self._summary_metric("kcal_carbs")
        if cached is not None:
            return cached
        return sum(dpm.meal.kcal_carbs for dpm in self.dailyplan_meals.all())

    @property
    def kcal_fat(self):
        cached = self._summary_metric("kcal_fat")
        if cached is not None:
            return cached
        return sum(dpm.meal.kcal_fat for dpm in self.dailyplan_meals.all())

    @property
    def total_kcal(self):
        cached = self._summary_metric("total_kcal")
        if cached is not None:
            return cached
        return self.kcal_protein + self.kcal_carbs + self.kcal_fat

    @property
    def alloc(self):
        cached = (self.summary_cache or {}).get("totals", {}).get("alloc")
        if cached is not None:
            return {
                "protein": cached.get("protein", 0),
                "carbs": cached.get("carbs", 0),
                "fat": cached.get("fat", 0),
            }

        total_kcal = self.total_kcal
        if total_kcal == 0:
            return {"protein": 0, "carbs": 0, "fat": 0}

        return {
            "protein": self.kcal_protein / total_kcal * 100,
            "carbs": self.kcal_carbs / total_kcal * 100,
            "fat": self.kcal_fat / total_kcal * 100,
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
