"""User-owned supplements and their planned daily-plan intakes.

Components are informational attributes, not composable nutrition entities.
Nothing in this module contributes to meal or daily-plan nutrition totals.
"""

from django.contrib.auth.models import User
from django.db import models


class Supplement(models.Model):
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="supplements")
    catalog_entry = models.ForeignKey("notas.SupplementCatalogEntry", null=True, blank=True, on_delete=models.SET_NULL, related_name="saved_supplements")
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True)
    form = models.CharField(max_length=32, blank=True)
    description = models.TextField(blank=True)
    user_information = models.TextField(blank=True)
    components = models.JSONField(default=list, blank=True)
    # Label values per default dose. They are descriptive and never feed meal or plan totals.
    nutrition = models.JSONField(default=dict, blank=True)
    default_quantity = models.DecimalField(max_digits=9, decimal_places=3, null=True, blank=True)
    default_unit = models.CharField(max_length=20, blank=True)
    list_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["list_order", "name", "id"]
        indexes = [models.Index(fields=["created_by", "list_order", "name"], name="supp_user_library_idx")]
        constraints = [models.UniqueConstraint(fields=["created_by", "catalog_entry"], condition=models.Q(catalog_entry__isnull=False), name="supp_one_catalog_copy_per_user")]

    def __str__(self):
        return self.name


class SupplementCatalogEntry(models.Model):
    """Reviewed global template; saving makes an independent user-owned copy."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True)
    form = models.CharField(max_length=32, blank=True)
    description = models.TextField(blank=True)
    components = models.JSONField(default=list, blank=True)
    nutrition = models.JSONField(default=dict, blank=True)
    default_quantity = models.DecimalField(max_digits=9, decimal_places=3, null=True, blank=True)
    default_unit = models.CharField(max_length=20, blank=True)
    source_name = models.CharField(max_length=120)
    source_url = models.URLField()
    reviewed_at = models.DateField()
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class SupplementIntake(models.Model):
    """A numbered group in a DailyPlan, never a standalone library item."""

    dailyplan = models.ForeignKey("notas.DailyPlan", on_delete=models.CASCADE, related_name="supplement_intakes")
    hour = models.TimeField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        indexes = [models.Index(fields=["dailyplan", "order"], name="supp_intake_plan_idx")]


class SupplementIntakePreset(models.Model):
    """Reusable user-owned composition offered when adding an intake to a plan."""

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="supplement_intake_presets")
    name = models.CharField(max_length=100)
    list_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["list_order", "name", "id"]
        indexes = [models.Index(fields=["created_by", "list_order", "name"], name="supp_preset_user_idx")]

    def __str__(self):
        return self.name


class SupplementIntakePresetItem(models.Model):
    preset = models.ForeignKey(SupplementIntakePreset, on_delete=models.CASCADE, related_name="items")
    supplement = models.ForeignKey(Supplement, null=True, blank=True, on_delete=models.SET_NULL)
    supplement_snapshot = models.JSONField(default=dict)
    quantity = models.DecimalField(max_digits=9, decimal_places=3)
    unit = models.CharField(max_length=20)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        indexes = [models.Index(fields=["preset", "order"], name="supp_preset_item_idx")]


class SupplementIntakeItem(models.Model):
    intake = models.ForeignKey(SupplementIntake, on_delete=models.CASCADE, related_name="items")
    supplement = models.ForeignKey(Supplement, null=True, blank=True, on_delete=models.SET_NULL)
    # Preserve the planned product if its library entry is later changed/deleted.
    supplement_snapshot = models.JSONField(default=dict)
    quantity = models.DecimalField(max_digits=9, decimal_places=3)
    unit = models.CharField(max_length=20)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        indexes = [models.Index(fields=["intake", "order"], name="supp_item_intake_idx")]


class PinnedSupplementIntakeExecution(models.Model):
    pinned_dailyplan = models.ForeignKey("notas.PinnedDailyPlan", on_delete=models.CASCADE, related_name="supplement_execution_events")
    local_date = models.DateField()
    intake_key = models.CharField(max_length=80)
    action = models.CharField(max_length=16, choices=(("completed", "Completed"), ("skipped", "Skipped"), ("reset", "Reset")))
    idempotency_key = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["pinned_dailyplan", "local_date", "created_at"], name="pin_supp_exec_day_idx")]


class CalendarizedSupplementIntakeExecution(models.Model):
    calendarized_day = models.ForeignKey("notas.CalendarizedDay", on_delete=models.CASCADE, related_name="supplement_execution_events")
    intake_key = models.CharField(max_length=80)
    action = models.CharField(max_length=16, choices=(("completed", "Completed"), ("skipped", "Skipped"), ("reset", "Reset")))
    idempotency_key = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["calendarized_day", "created_at"], name="cal_supp_exec_day_idx")]
