from django.contrib.auth.models import User
from django.db import models


class WebPushSubscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="web_push_subscriptions",
    )
    endpoint = models.TextField(unique=True)
    endpoint_fingerprint = models.CharField(max_length=64, db_index=True)
    p256dh_key = models.CharField(max_length=255)
    auth_key = models.CharField(max_length=255)
    user_agent = models.TextField(blank=True)
    device_label = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(
                fields=["user", "is_active"],
                name="push_user_active_idx",
            ),
        ]

    def __str__(self):
        label = self.device_label or self.endpoint_fingerprint[:12]
        return f"{self.user} · {label}"


class ApplePushSubscription(models.Model):
    ENVIRONMENT_SANDBOX = "sandbox"
    ENVIRONMENT_PRODUCTION = "production"
    ENVIRONMENT_CHOICES = (
        (ENVIRONMENT_SANDBOX, "Sandbox"),
        (ENVIRONMENT_PRODUCTION, "Production"),
    )

    device_session = models.OneToOneField(
        "notas.OAuthDeviceSession",
        on_delete=models.CASCADE,
        related_name="apple_push_subscription",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="apple_push_subscriptions",
    )
    device_token = models.CharField(max_length=200)
    token_fingerprint = models.CharField(max_length=64, unique=True)
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES)
    is_active = models.BooleanField(default=True, db_index=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(
                fields=["user", "is_active"],
                name="apns_user_active_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} · iOS {self.token_fingerprint[:12]}"


class ScheduledNotificationEvent(models.Model):
    TYPE_DAILY_PLAN = "daily_plan"
    TYPE_MEAL_REMINDER = "meal_reminder"
    TYPE_CHOICES = (
        (TYPE_DAILY_PLAN, "Daily plan"),
        (TYPE_MEAL_REMINDER, "Meal reminder"),
    )

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_DISPATCHED = "dispatched"
    STATUS_SKIPPED = "skipped"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_DISPATCHED, "Dispatched"),
        (STATUS_SKIPPED, "Skipped"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    calendarization = models.ForeignKey(
        "notas.ProgramCalendarization",
        on_delete=models.CASCADE,
        related_name="notification_events",
    )
    calendarized_day = models.ForeignKey(
        "notas.CalendarizedDay",
        on_delete=models.CASCADE,
        related_name="notification_events",
    )
    event_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    event_key = models.CharField(max_length=180, unique=True)
    meal_snapshot_key = models.CharField(max_length=80, blank=True)
    local_scheduled_date = models.DateField()
    local_scheduled_time = models.TimeField()
    timezone_name = models.CharField(max_length=64)
    scheduled_for_utc = models.DateTimeField(db_index=True)
    available_until_utc = models.DateTimeField()
    dst_resolution = models.CharField(max_length=32, default="exact")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    skip_reason = models.CharField(max_length=80, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_for_utc", "id"]
        indexes = [
            models.Index(
                fields=["status", "scheduled_for_utc"],
                name="push_event_due_idx",
            ),
            models.Index(
                fields=["calendarization", "status"],
                name="push_event_cal_status_idx",
            ),
        ]

    def __str__(self):
        return self.event_key


class NotificationDelivery(models.Model):
    CHANNEL_WEB_PUSH = "web_push"
    CHANNEL_APNS = "apns"
    CHANNEL_CHOICES = (
        (CHANNEL_WEB_PUSH, "Web Push"),
        (CHANNEL_APNS, "Apple Push Notification service"),
    )

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
        (STATUS_EXPIRED, "Expired"),
    )

    event = models.ForeignKey(
        ScheduledNotificationEvent,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    subscription = models.ForeignKey(
        WebPushSubscription,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deliveries",
    )
    apple_subscription = models.ForeignKey(
        ApplePushSubscription,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deliveries",
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default=CHANNEL_WEB_PUSH)
    subscription_fingerprint = models.CharField(max_length=64)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "subscription_fingerprint"],
                name="push_unique_event_device",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(channel="web_push", apple_subscription__isnull=True)
                    | models.Q(channel="apns", subscription__isnull=True)
                ),
                name="push_delivery_channel_target",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="push_delivery_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event.event_key} · {self.subscription_fingerprint[:12]}"
