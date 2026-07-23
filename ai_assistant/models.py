from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AIUsageEvent(models.Model):
    """Economic/operational usage record for one AI Assistant turn.

    Tokens remain an internal cost metric. Commercial limits are expressed as
    AI credits through quota and ledger models.
    """

    class Status(models.TextChoices):
        COMPLETED = "completed", "Completed"
        DEGRADED = "degraded", "Degraded"
        ERROR = "error", "Error"
        BLOCKED = "blocked", "Blocked"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_usage_events",
    )
    period = models.CharField(max_length=7, db_index=True)
    conversation_id = models.CharField(max_length=80, blank=True)
    turn_id = models.CharField(max_length=80, blank=True)

    action_type = models.CharField(max_length=80, db_index=True)
    provider = models.CharField(max_length=60, blank=True)
    model_name = models.CharField(max_length=120, blank=True)

    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    cached_input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    total_tokens = models.PositiveIntegerField(null=True, blank=True)
    estimated_cost_usd = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    charged_credits = models.PositiveIntegerField(default=0)
    credit_plan_code = models.CharField(max_length=50, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED, db_index=True)
    error_type = models.CharField(max_length=120, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    tool_calls_count = models.PositiveIntegerField(default=0)

    usage_payload = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "period"], name="ai_usage_user_period_idx"),
            models.Index(fields=["action_type", "created_at"], name="ai_usage_action_created_idx"),
            models.Index(fields=["provider", "model_name"], name="ai_usage_provider_model_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.period} · {self.action_type} · {self.total_tokens or 0} tokens"



class AIUserCreditQuota(models.Model):
    """Monthly AI credit quota snapshot for one user.

    Credits are the commercial unit for My Scoope memberships. Token and USD
    costs remain internal observability details in `AIUsageEvent`.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_credit_quotas",
    )
    period = models.CharField(max_length=7, db_index=True)
    plan_code = models.CharField(max_length=50, db_index=True)
    monthly_credit_limit = models.PositiveIntegerField(default=0)
    daily_credit_limit = models.PositiveIntegerField(default=0)
    credits_used = models.PositiveIntegerField(default=0)
    hard_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period", "user_id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "period"], name="ai_credit_quota_user_period_unique"),
        ]
        indexes = [
            models.Index(fields=["period", "plan_code"], name="ai_cr_quota_period_plan_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.period} · {self.credits_used}/{self.monthly_credit_limit} credits"


class AICreditLedger(models.Model):
    """Append-only AI credit ledger entry linked to usage observability."""

    class Kind(models.TextChoices):
        CHARGE = "charge", "Charge"
        ADJUSTMENT = "adjustment", "Adjustment"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_credit_ledger_entries",
    )
    usage_event = models.ForeignKey(
        AIUsageEvent,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="credit_ledger_entries",
    )
    period = models.CharField(max_length=7, db_index=True)
    plan_code = models.CharField(max_length=50, db_index=True)
    action_type = models.CharField(max_length=80, db_index=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.CHARGE)
    credits = models.PositiveIntegerField()
    reason = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "period"], name="ai_cr_ledger_user_period_idx"),
            models.Index(fields=["action_type", "created_at"], name="ai_credit_action_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.period} · {self.user} · {self.credits} credits"


class AIPreparedAction(models.Model):
    """A reviewable product action prepared by the assistant.

    Preparation may persist this audit record, but it never mutates the target
    product entity. A trusted server-side UI event is required for commit.
    """

    class Status(models.TextChoices):
        PREPARED = "prepared", "Prepared"
        COMMITTED = "committed", "Committed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        FAILED = "failed", "Failed"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_prepared_actions",
    )
    action_key = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=180)
    summary = models.TextField(blank=True)
    target_type = models.CharField(max_length=60, blank=True)
    target_id = models.PositiveBigIntegerField(null=True, blank=True)
    target_version = models.CharField(max_length=160, blank=True)
    arguments = models.JSONField(default=dict, blank=True)
    preview = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    destructive = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PREPARED,
        db_index=True,
    )
    expires_at = models.DateTimeField()
    committed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["user", "status", "created_at"],
                name="ai_prep_user_status_idx",
            ),
        ]

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()

    def __str__(self) -> str:
        return f"{self.action_key} · {self.user} · {self.status}"
