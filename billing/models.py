from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import AccountPlan


class PaymentProvider(models.TextChoices):
    PADDLE = "paddle", "Paddle"
    MERCADO_PAGO = "mercado_pago", "Mercado Pago"
    APPLE_APP_STORE = "apple_app_store", "Apple App Store"
    GOOGLE_PLAY = "google_play", "Google Play"


class AppleAppAccountToken(models.Model):
    """Stable opaque UUID used to bind StoreKit evidence to one My Scoope account."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="apple_app_account_token",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user_id"]

    def __str__(self) -> str:
        return f"Apple account token · {self.user_id}"


class BillingOffer(models.Model):
    """Canonical sellable offer for one account plan.

    This is the runtime authority for public price, currency and billing cadence.
    Provider catalog records map an offer to Paddle, Apple or Google without
    duplicating the customer-facing commercial decision.
    """

    class Interval(models.TextChoices):
        MONTH = "month", "Month"
        YEAR = "year", "Year"

    code = models.SlugField(
        max_length=80,
        unique=True,
        help_text="Stable commercial offer identifier, for example basic-monthly.",
    )
    account_plan = models.ForeignKey(AccountPlan, on_delete=models.PROTECT, related_name="billing_offers")
    currency = models.CharField(max_length=3, default="CLP")
    amount_minor = models.PositiveBigIntegerField(help_text="Canonical price in the currency's minor unit.")
    interval = models.CharField(max_length=16, choices=Interval.choices)
    interval_count = models.PositiveSmallIntegerField(default=1)
    active = models.BooleanField(default=True, db_index=True)
    public = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveSmallIntegerField(default=100)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["account_plan__display_order", "display_order", "amount_minor"]
        constraints = [
            models.UniqueConstraint(
                fields=["account_plan", "interval", "interval_count"],
                condition=models.Q(active=True, public=True),
                name="billing_offer_public_cadence_uq",
            ),
            models.CheckConstraint(
                condition=models.Q(amount_minor__gt=0),
                name="billing_offer_amount_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(interval_count__gt=0),
                name="billing_offer_interval_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.account_plan.name} · {self.interval_count} {self.get_interval_display()}"


class BillingProduct(models.Model):
    """Immutable provider-catalog mapping for one canonical commercial offer."""

    class Kind(models.TextChoices):
        SUBSCRIPTION = "subscription", "Subscription"

    class Interval(models.TextChoices):
        MONTH = "month", "Month"
        YEAR = "year", "Year"

    class Environment(models.TextChoices):
        SANDBOX = "sandbox", "Sandbox"
        LIVE = "live", "Live"

    provider = models.CharField(max_length=32, choices=PaymentProvider.choices, db_index=True)
    environment = models.CharField(
        max_length=16,
        choices=Environment.choices,
        default=Environment.LIVE,
        db_index=True,
    )
    external_product_id = models.CharField(max_length=160)
    external_price_id = models.CharField(max_length=160, blank=True)
    offer = models.ForeignKey(
        BillingOffer,
        on_delete=models.PROTECT,
        related_name="provider_products",
        null=True,
        blank=True,
    )
    account_plan = models.ForeignKey(AccountPlan, on_delete=models.PROTECT, related_name="billing_products")
    kind = models.CharField(max_length=24, choices=Kind.choices, default=Kind.SUBSCRIPTION)
    currency = models.CharField(max_length=3, default="CLP")
    amount_minor = models.PositiveBigIntegerField(help_text="Price in the currency's minor unit.")
    interval = models.CharField(max_length=16, choices=Interval.choices, default=Interval.MONTH)
    interval_count = models.PositiveSmallIntegerField(default=1)
    active = models.BooleanField(default=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider", "account_plan__display_order", "amount_minor"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "environment", "external_product_id"],
                condition=models.Q(external_price_id=""),
                name="billprod_provider_env_product_uq",
            ),
            models.UniqueConstraint(
                fields=["provider", "environment", "external_price_id"],
                condition=~models.Q(external_price_id=""),
                name="billprod_provider_env_price_uq",
            ),
            models.UniqueConstraint(
                fields=["provider", "environment", "offer"],
                condition=models.Q(active=True, offer__isnull=False),
                name="billprod_active_offer_env_uq",
            ),
            models.CheckConstraint(
                condition=models.Q(interval_count__gt=0),
                name="billing_product_interval_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_provider_display()} · {self.account_plan.name}"

    def clean(self):
        super().clean()
        errors = {}
        if self.provider == PaymentProvider.PADDLE and self.active:
            if not self.external_product_id.startswith("pro_"):
                errors["external_product_id"] = "An active Paddle mapping requires a pro_ product ID."
            if not self.external_price_id.startswith("pri_"):
                errors["external_price_id"] = "An active Paddle mapping requires a pri_ price ID."
            if self.offer_id is None:
                errors["offer"] = "An active Paddle mapping requires a canonical offer."
        if self.active and self.offer_id is not None:
            snapshot_fields = {
                "account_plan": (self.account_plan_id, self.offer.account_plan_id),
                "amount_minor": (self.amount_minor, self.offer.amount_minor),
                "currency": (self.currency, self.offer.currency),
                "interval": (self.interval, self.offer.interval),
                "interval_count": (self.interval_count, self.offer.interval_count),
            }
            for field, (actual, expected) in snapshot_fields.items():
                if actual != expected:
                    errors[field] = "Active provider mapping must match its canonical offer."
        if errors:
            raise ValidationError(errors)


class ProviderSubscription(models.Model):
    """Provider-side agreement; accounts.AccountSubscription remains the entitlement projection."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        AUTHORIZED = "authorized", "Authorized"
        PAUSED = "paused", "Paused"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"
        EXPIRED = "expired", "Expired"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="billing_subscriptions")
    product = models.ForeignKey(BillingProduct, on_delete=models.PROTECT, related_name="subscriptions")
    provider = models.CharField(max_length=32, choices=PaymentProvider.choices, db_index=True)
    external_subscription_id = models.CharField(max_length=160)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING, db_index=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_subscription_id"],
                name="billing_subscription_provider_external_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.get_provider_display()} · {self.status}"


class BillingPayment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELED = "canceled", "Canceled"
        REFUNDED = "refunded", "Refunded"
        CHARGED_BACK = "charged_back", "Charged back"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="billing_payments")
    subscription = models.ForeignKey(
        ProviderSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    provider = models.CharField(max_length=32, choices=PaymentProvider.choices, db_index=True)
    external_payment_id = models.CharField(max_length=160)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING, db_index=True)
    amount_minor = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3, default="CLP")
    approved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_payment_id"],
                name="billing_payment_provider_external_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_provider_display()} · {self.external_payment_id} · {self.status}"


class BillingEvent(models.Model):
    """Immutable, idempotent inbox row for an authenticated provider notification."""

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        IGNORED = "ignored", "Ignored"
        FAILED = "failed", "Failed"

    provider = models.CharField(max_length=32, choices=PaymentProvider.choices, db_index=True)
    external_event_id = models.CharField(max_length=190)
    event_type = models.CharField(max_length=100, db_index=True)
    resource_id = models.CharField(max_length=190, blank=True)
    signature_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_event_id"],
                name="billing_event_provider_external_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_provider_display()} · {self.event_type} · {self.status}"


class TaxDocument(models.Model):
    """Outbox and audit state for a tax document associated with one approved payment."""

    class Provider(models.TextChoices):
        OPENFACTURA = "openfactura", "OpenFactura"

    class Kind(models.TextChoices):
        ELECTRONIC_RECEIPT = "electronic_receipt", "Boleta electrónica"
        EXEMPT_ELECTRONIC_RECEIPT = "exempt_electronic_receipt", "Boleta electrónica exenta"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ISSUING = "issuing", "Issuing"
        ISSUED = "issued", "Issued"
        ACCEPTED = "accepted", "Accepted"
        ACCEPTED_WITH_OBJECTIONS = "accepted_with_objections", "Accepted with objections"
        REJECTED = "rejected", "Rejected"
        VOIDED = "voided", "Voided"
        FAILED = "failed", "Failed"

    payment = models.OneToOneField(BillingPayment, on_delete=models.PROTECT, related_name="tax_document")
    provider = models.CharField(max_length=24, choices=Provider.choices, default=Provider.OPENFACTURA)
    kind = models.CharField(max_length=40, choices=Kind.choices, default=Kind.ELECTRONIC_RECEIPT)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING, db_index=True)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    external_document_id = models.CharField(max_length=190, blank=True)
    folio = models.CharField(max_length=40, blank=True)
    document_token = models.CharField(max_length=190, blank=True)
    request_payload = models.JSONField(default=dict, blank=True)
    response_metadata = models.JSONField(default=dict, blank=True)
    last_error = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    first_attempt_at = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    adjustment_required = models.BooleanField(default=False, db_index=True)
    adjustment_reason = models.TextField(blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.get_provider_display()} · {self.payment_id} · {self.status}"
