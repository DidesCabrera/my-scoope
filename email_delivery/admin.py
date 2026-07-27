from django.contrib import admin

from email_delivery.models import EmailDeliveryAttempt


@admin.register(EmailDeliveryAttempt)
class EmailDeliveryAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "category",
        "status",
        "recipient_email",
        "actor",
        "reason",
    )
    list_filter = ("category", "status", "provider")
    search_fields = (
        "recipient_email",
        "subject",
        "source_model",
        "source_id",
        "idempotency_key",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "sent_at",
        "provider_message_id",
    )
