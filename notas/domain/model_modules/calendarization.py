from datetime import time

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q


class ProgramCalendarization(models.Model):
    STATUS_SCHEDULED = "scheduled"
    STATUS_ACTIVE = "active"
    STATUS_PAUSED = "paused"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    CURRENT_STATUSES = (STATUS_SCHEDULED, STATUS_ACTIVE, STATUS_PAUSED)
    STATUS_CHOICES = (
        (STATUS_SCHEDULED, "Programada"),
        (STATUS_ACTIVE, "Activa"),
        (STATUS_PAUSED, "Pausada"),
        (STATUS_COMPLETED, "Completada"),
        (STATUS_CANCELLED, "Cancelada"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="program_calendarizations",
    )
    source_program = models.ForeignKey(
        "notas.Program",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="calendarizations",
    )
    program_name_snapshot = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    timezone_name = models.CharField(max_length=64, default="UTC")
    daily_notification_time = models.TimeField(default=time(7, 0))
    daily_notifications_enabled = models.BooleanField(default=True)
    meal_notifications_enabled = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED,
        db_index=True,
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status__in=("scheduled", "active", "paused")),
                name="cal_one_current_per_user",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="cal_end_not_before_start",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "status", "start_date"],
                name="cal_user_status_start_idx",
            ),
            models.Index(
                fields=["status", "end_date"],
                name="cal_status_end_idx",
            ),
        ]

    def __str__(self):
        return f"{self.program_name_snapshot} · {self.start_date}"

    @property
    def is_current(self):
        return self.status in self.CURRENT_STATUSES


class CalendarizedDay(models.Model):
    calendarization = models.ForeignKey(
        ProgramCalendarization,
        on_delete=models.CASCADE,
        related_name="days",
    )
    calendar_date = models.DateField()
    week_number = models.PositiveSmallIntegerField()
    day_number = models.PositiveSmallIntegerField()
    source_program_day_id = models.PositiveBigIntegerField(null=True, blank=True)
    source_dailyplan_id = models.PositiveBigIntegerField(null=True, blank=True)
    plan_snapshot = models.JSONField(null=True, blank=True)
    snapshot_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["calendar_date", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["calendarization", "calendar_date"],
                name="cal_unique_calendar_date",
            ),
            models.UniqueConstraint(
                fields=["calendarization", "week_number", "day_number"],
                name="cal_unique_program_slot",
            ),
            models.CheckConstraint(
                condition=Q(day_number__gte=1, day_number__lte=7),
                name="cal_day_number_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=["calendarization", "calendar_date"],
                name="cal_day_lookup_idx",
            ),
        ]

    def __str__(self):
        return f"{self.calendarization} · {self.calendar_date}"

    @property
    def has_plan(self):
        return bool(self.plan_snapshot)


class CalendarizedMealExecution(models.Model):
    ACTION_COMPLETED = "completed"
    ACTION_SKIPPED = "skipped"
    ACTION_RESET = "reset"
    ACTION_CHOICES = (
        (ACTION_COMPLETED, "Completed"),
        (ACTION_SKIPPED, "Skipped"),
        (ACTION_RESET, "Reset"),
    )

    calendarized_day = models.ForeignKey(
        CalendarizedDay,
        on_delete=models.CASCADE,
        related_name="meal_execution_events",
    )
    meal_snapshot_key = models.CharField(max_length=80)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    idempotency_key = models.CharField(max_length=120, unique=True)
    note = models.CharField(max_length=500, blank=True)
    occurred_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(
                fields=["calendarized_day", "created_at"],
                name="cal_meal_exec_day_idx",
            ),
        ]

    def __str__(self):
        return f"{self.calendarized_day_id} · {self.meal_snapshot_key} · {self.action}"


class CalendarizationMeasurementContext(models.Model):
    calendarization = models.ForeignKey(
        ProgramCalendarization,
        on_delete=models.CASCADE,
        related_name="measurement_contexts",
    )
    calendarized_day = models.ForeignKey(
        CalendarizedDay,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="measurement_contexts",
    )
    weight_log = models.ForeignKey(
        "notas.WeightLog",
        on_delete=models.CASCADE,
        related_name="calendarization_contexts",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["weight_log__date", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["calendarization", "weight_log"],
                name="cal_unique_measure_context",
            ),
        ]
        indexes = [
            models.Index(
                fields=["calendarization", "created_at"],
                name="cal_measure_context_idx",
            ),
        ]

    def __str__(self):
        return f"{self.calendarization_id} · weight {self.weight_log_id}"


class CalendarizationReview(models.Model):
    calendarization = models.ForeignKey(
        ProgramCalendarization,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    energy_score = models.PositiveSmallIntegerField(null=True, blank=True)
    hunger_score = models.PositiveSmallIntegerField(null=True, blank=True)
    training_performance_score = models.PositiveSmallIntegerField(null=True, blank=True)
    note = models.CharField(max_length=1000, blank=True)
    summary_snapshot = models.JSONField(default=dict)
    idempotency_key = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_end", "-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(period_end__gte=models.F("period_start")),
                name="cal_review_period_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["calendarization", "period_end"],
                name="cal_review_period_idx",
            ),
        ]

    def __str__(self):
        return f"{self.calendarization_id} · {self.period_start}–{self.period_end}"


class CalendarizationRevision(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPLIED = "applied"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_APPLIED, "Applied"),
        (STATUS_REJECTED, "Rejected"),
    )

    calendarization = models.ForeignKey(
        ProgramCalendarization,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    review = models.ForeignKey(
        CalendarizationReview,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="revisions",
    )
    effective_from = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    before_snapshot = models.JSONField(default=dict)
    after_snapshot = models.JSONField(default=dict)
    rationale = models.CharField(max_length=1000)
    idempotency_key = models.CharField(max_length=120, unique=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["calendarization", "status", "effective_from"],
                name="cal_revision_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.calendarization_id} · {self.effective_from} · {self.status}"
