from django.contrib.auth.models import User
from django.db import models

from notas.domain.model_modules.dailyplans import DailyPlan


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

    summary_cache = models.JSONField(default=dict, blank=True)
    summary_cache_updated_at = models.DateTimeField(null=True, blank=True)

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
        cached = (self.summary_cache or {}).get("filled_days_count")
        if cached is not None:
            return cached
        return self.program_dailyplan.count()

    @property
    def empty_days_count(self):
        return max(self.duration_days - self.filled_days_count, 0)

    @property
    def protein(self):
        cached = (self.summary_cache or {}).get("program_totals", {}).get("protein")
        if cached is not None:
            return cached
        return sum(day.dailyplan.protein for day in self.program_dailyplan.all())

    @property
    def carbs(self):
        cached = (self.summary_cache or {}).get("program_totals", {}).get("carbs")
        if cached is not None:
            return cached
        return sum(day.dailyplan.carbs for day in self.program_dailyplan.all())

    @property
    def fat(self):
        cached = (self.summary_cache or {}).get("program_totals", {}).get("fat")
        if cached is not None:
            return cached
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
        cached = (self.summary_cache or {}).get("program_totals", {}).get("kcal_protein")
        if cached is not None:
            return cached
        return sum(day.dailyplan.kcal_protein for day in self.program_dailyplan.all())

    @property
    def kcal_carbs(self):
        cached = (self.summary_cache or {}).get("program_totals", {}).get("kcal_carbs")
        if cached is not None:
            return cached
        return sum(day.dailyplan.kcal_carbs for day in self.program_dailyplan.all())

    @property
    def kcal_fat(self):
        cached = (self.summary_cache or {}).get("program_totals", {}).get("kcal_fat")
        if cached is not None:
            return cached
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
