from django.contrib.auth.models import User
from django.db import models

from notas.domain.model_modules.food import Food
from notas.domain.services.nutrition import compute_meal_nutrition

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
        if self.kcal_protein_cached is not None:
            return self.kcal_protein_cached
        return sum(mf.kcal_protein for mf in self.meal_food_set.all())

    @property
    def kcal_carbs(self):
        if self.kcal_carbs_cached is not None:
            return self.kcal_carbs_cached
        return sum(mf.kcal_carbs for mf in self.meal_food_set.all())

    @property
    def kcal_fat(self):
        if self.kcal_fat_cached is not None:
            return self.kcal_fat_cached
        return sum(mf.kcal_fat for mf in self.meal_food_set.all())

    @property
    def total_kcal(self):
        if self.total_kcal_cached is not None:
            return self.total_kcal_cached
        return self.kcal_protein + self.kcal_carbs + self.kcal_fat

    @property
    def alloc(self):
        if (
            self.alloc_protein_cached is not None
            and self.alloc_carbs_cached is not None
            and self.alloc_fat_cached is not None
        ):
            return {
                "protein": self.alloc_protein_cached,
                "carbs": self.alloc_carbs_cached,
                "fat": self.alloc_fat_cached,
            }

        total_kcal = self.total_kcal
        if total_kcal == 0:
            return {"protein": 0, "carbs": 0, "fat": 0}

        return {
            "protein": self.kcal_protein / total_kcal * 100,
            "carbs": self.kcal_carbs / total_kcal * 100,
            "fat": self.kcal_fat / total_kcal * 100,
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
# ACCESS
# ==================================================

class MealAccess(models.Model):
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    granted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
