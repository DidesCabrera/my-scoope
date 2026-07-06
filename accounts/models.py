from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class AccountPlan(models.Model):
    """Commercial account plan.

    This model belongs to the `accounts` domain and is intentionally separate
    from `notas.Plan`, which remains the legacy/current compatibility model for
    older nutritional permissions while the ACC migration progresses.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    slug = models.SlugField(
        max_length=60,
        unique=True,
        help_text="Stable commercial identifier. Do not depend on the display name.",
    )
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    display_order = models.PositiveSmallIntegerField(default=100)

    included_monthly_credits = models.PositiveIntegerField(
        default=0,
        help_text="Credits granted by this plan in a monthly period. Zero means no included credits.",
    )
    daily_credit_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional daily credit cap. Empty means no explicit daily cap.",
    )
    monthly_credit_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional monthly credit cap. Empty means no explicit monthly cap.",
    )

    entitlements = models.JSONField(
        default=dict,
        blank=True,
        help_text="Commercial feature flags and limits resolved by accounts services.",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(fields=["status", "display_order"], name="acct_plan_status_order_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE


class AccountSubscription(models.Model):
    """Current commercial subscription for a user.

    The first ACC implementation keeps a single account subscription per user.
    Billing providers, invoices and historical subscription events remain out of
    scope for this cycle.
    """

    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"
        EXPIRED = "expired", "Expired"

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        SEED = "seed", "Seed"
        MIGRATION = "migration", "Migration"
        BILLING = "billing", "Billing"
        INTERNAL = "internal", "Internal"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_subscription",
    )
    plan = models.ForeignKey(
        AccountPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)

    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "user_id"]
        indexes = [
            models.Index(fields=["status", "current_period_end"], name="acct_sub_status_period_idx"),
            models.Index(fields=["source", "created_at"], name="acct_sub_source_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.plan.slug} · {self.status}"

    @property
    def is_active(self) -> bool:
        return self.status in {self.Status.TRIALING, self.Status.ACTIVE}

class CreditWallet(models.Model):
    """Commercial credit wallet owned by the accounts domain.

    Credits are the user-facing commercial unit. Tokens and provider costs stay
    in AI operational records and can later be correlated through ledger
    references.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="credit_wallet",
    )
    balance = models.PositiveIntegerField(default=0)
    reserved_balance = models.PositiveIntegerField(
        default=0,
        help_text="Credits temporarily reserved for in-flight operations.",
    )
    period = models.CharField(
        max_length=7,
        blank=True,
        db_index=True,
        help_text="Current wallet accounting period in YYYY-MM format when applicable.",
    )
    plan_snapshot_code = models.CharField(
        max_length=60,
        blank=True,
        help_text="Plan slug/code that granted or last refreshed this wallet balance.",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user_id"]
        indexes = [
            models.Index(fields=["period", "plan_snapshot_code"], name="acct_wallet_period_plan_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.available_credits} available credits"

    @property
    def available_credits(self) -> int:
        return max(int(self.balance or 0) - int(self.reserved_balance or 0), 0)

    @property
    def has_reserved_credits(self) -> bool:
        return int(self.reserved_balance or 0) > 0


class CreditLedger(models.Model):
    """Append-only commercial credit ledger.

    Every balance correction must be represented by a new entry instead of
    mutating a historical movement. ACC04/ACC05 will connect AI reservations and
    real usage events to this ledger.
    """

    class Kind(models.TextChoices):
        GRANT = "grant", "Grant"
        RESERVE = "reserve", "Reserve"
        CONSUME = "consume", "Consume"
        RELEASE = "release", "Release"
        REFUND = "refund", "Refund"
        ADJUSTMENT = "adjustment", "Adjustment"
        EXPIRE = "expire", "Expire"

    wallet = models.ForeignKey(
        CreditWallet,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="credit_ledger_entries",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, db_index=True)
    credits_delta = models.IntegerField(
        help_text="Signed credit movement. Grants/refunds are positive; consumes/expirations are negative.",
    )
    reserved_delta = models.IntegerField(
        default=0,
        help_text="Signed reserved-credit movement for reservation lifecycle auditing.",
    )
    balance_after = models.IntegerField(help_text="Wallet balance after this movement was applied.")
    reserved_balance_after = models.IntegerField(
        default=0,
        help_text="Wallet reserved balance after this movement was applied.",
    )
    period = models.CharField(max_length=7, blank=True, db_index=True)
    plan_snapshot_code = models.CharField(max_length=60, blank=True)
    reference_type = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional external reference type, for example ai_usage_event.",
    )
    reference_id = models.CharField(max_length=120, blank=True)
    reason = models.CharField(max_length=160, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "period"], name="acct_ledger_user_period_idx"),
            models.Index(fields=["kind", "created_at"], name="acct_ledger_kind_created_idx"),
            models.Index(fields=["reference_type", "reference_id"], name="acct_ledger_reference_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.kind} · {self.credits_delta} credits · {self.user}"

    def save(self, *args, **kwargs):
        if self.pk and CreditLedger.objects.filter(pk=self.pk).exists():
            from django.core.exceptions import ValidationError

            raise ValidationError("CreditLedger entries are append-only and cannot be updated.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from django.core.exceptions import ValidationError

        raise ValidationError("CreditLedger entries are append-only and cannot be deleted.")

