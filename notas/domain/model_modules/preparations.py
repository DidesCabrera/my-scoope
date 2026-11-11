"""Operational preparations. Catalog mirrors are never read during meal calculation."""

import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Preparation(models.Model):
    """Stable identity for curated and user-owned preparations."""

    catalog_ref = models.UUIDField(default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=255)
    is_global = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    current_version = models.ForeignKey(
        "PreparationVersion", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    def __str__(self):
        return self.name


class PreparationVersion(models.Model):
    """Immutable operational revision from the catalog or personal authoring."""

    preparation = models.ForeignKey(Preparation, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    release_version = models.CharField(max_length=64)
    yield_g = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(0.001)])
    default_portion_g = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(0.001)])
    household_label = models.CharField(max_length=80)
    protein_g = models.DecimalField(max_digits=12, decimal_places=5)
    carbs_g = models.DecimalField(max_digits=12, decimal_places=5)
    fat_g = models.DecimalField(max_digits=12, decimal_places=5)
    sodium_mg = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)
    allergens = models.JSONField(default=list)
    allergen_status = models.CharField(max_length=20, default="unknown")
    evidence = models.JSONField(default=dict)
    ingredients_snapshot = models.JSONField(default=list)
    content_sha256 = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["preparation", "version"], name="unique_operational_preparation_version")]

    def save(self, *args, **kwargs):
        if self.pk and PreparationVersion.objects.filter(pk=self.pk).exists():
            from django.core.exceptions import ValidationError
            raise ValidationError("Operational preparation versions are immutable.")
        super().save(*args, **kwargs)


class PreparationIngredient(models.Model):
    """Navigable ingredient link; all nutrition is frozen in the version snapshot."""

    version = models.ForeignKey(PreparationVersion, on_delete=models.PROTECT, related_name="ingredients")
    food = models.ForeignKey("notas.Food", on_delete=models.PROTECT)
    quantity_g = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(0.001)])
    preparation_state = models.CharField(max_length=30)
    is_condiment = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def save(self, *args, **kwargs):
        if self.pk and PreparationIngredient.objects.filter(pk=self.pk).exists():
            from django.core.exceptions import ValidationError
            raise ValidationError("Operational preparation ingredients are immutable.")
        super().save(*args, **kwargs)


class MealPreparation(models.Model):
    """One served portion. The selected unit and its equivalent grams are retained."""

    meal = models.ForeignKey("notas.Meal", on_delete=models.CASCADE, related_name="meal_preparation_set")
    preparation = models.ForeignKey(Preparation, on_delete=models.PROTECT)
    version = models.ForeignKey(PreparationVersion, on_delete=models.PROTECT)
    quantity_g = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(0.001)])
    selected_units = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    selection_mode = models.CharField(max_length=8, choices=[("units", "Units"), ("grams", "Grams")])
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    @property
    def factor(self):
        return float(self.quantity_g / self.version.yield_g)

    @property
    def protein(self):
        return float(self.version.protein_g) * self.factor

    @property
    def carbs(self):
        return float(self.version.carbs_g) * self.factor

    @property
    def fat(self):
        return float(self.version.fat_g) * self.factor

    @property
    def kcal_protein(self):
        return self.protein * 4

    @property
    def kcal_carbs(self):
        return self.carbs * 4

    @property
    def kcal_fat(self):
        return self.fat * 9

    @property
    def total_kcal(self):
        return self.kcal_protein + self.kcal_carbs + self.kcal_fat
