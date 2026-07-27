from django.conf import settings
from django.db import models


class EmailDeliveryAttempt(models.Model):
    CATEGORY_EMAIL_VERIFICATION = "email_verification"
    CATEGORY_PASSWORD_RESET = "password_reset"
    CATEGORY_SHARE_INVITATION = "share_invitation"
    CATEGORY_ACCOUNT = "account"
    CATEGORY_CHOICES = (
        (CATEGORY_EMAIL_VERIFICATION, "Email verification"),
        (CATEGORY_PASSWORD_RESET, "Password reset"),
        (CATEGORY_SHARE_INVITATION, "Share invitation"),
        (CATEGORY_ACCOUNT, "Account"),
    )

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_SUPPRESSED = "suppressed"
    STATUS_RATE_LIMITED = "rate_limited"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
        (STATUS_SUPPRESSED, "Suppressed"),
        (STATUS_RATE_LIMITED, "Rate limited"),
    )

    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="email_delivery_attempts",
    )
    recipient_email = models.EmailField(db_index=True)
    subject = models.CharField(max_length=255, blank=True)
    source_model = models.CharField(max_length=120, blank=True)
    source_id = models.CharField(max_length=80, blank=True)
    idempotency_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
    )
    provider = models.CharField(max_length=40, default="smtp")
    provider_message_id = models.CharField(max_length=255, blank=True)
    reason = models.CharField(max_length=80, blank=True)
    error_code = models.CharField(max_length=120, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["category", "status", "created_at"],
                name="email_category_status_idx",
            ),
            models.Index(
                fields=["actor", "category", "created_at"],
                name="email_actor_category_idx",
            ),
        ]

    def __str__(self):
        return f"{self.category} · {self.recipient_email} · {self.status}"
