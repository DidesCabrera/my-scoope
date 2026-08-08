from django.contrib import admin

from billing.models import (
    AppleAppAccountToken,
    BillingEvent,
    BillingPayment,
    BillingProduct,
    ProviderSubscription,
    TaxDocument,
)


@admin.register(AppleAppAccountToken)
class AppleAppAccountTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "token", "created_at")
    search_fields = ("user__username", "user__email", "token")
    readonly_fields = ("user", "token", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BillingProduct)
class BillingProductAdmin(admin.ModelAdmin):
    list_display = ("provider", "account_plan", "amount_minor", "currency", "interval", "active")
    list_filter = ("provider", "kind", "interval", "active")
    search_fields = ("external_product_id", "account_plan__name", "account_plan__slug")


@admin.register(ProviderSubscription)
class ProviderSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "product", "status", "current_period_end")
    list_filter = ("provider", "status", "product")
    search_fields = ("user__username", "user__email", "external_subscription_id")
    autocomplete_fields = ("user", "product")


@admin.register(BillingPayment)
class BillingPaymentAdmin(admin.ModelAdmin):
    list_display = ("external_payment_id", "user", "provider", "status", "amount_minor", "currency", "approved_at")
    list_filter = ("provider", "status", "currency")
    search_fields = ("external_payment_id", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(BillingEvent)
class BillingEventAdmin(admin.ModelAdmin):
    list_display = ("external_event_id", "provider", "event_type", "status", "signature_verified", "received_at")
    list_filter = ("provider", "status", "signature_verified", "event_type")
    search_fields = ("external_event_id", "resource_id")
    readonly_fields = ("provider", "external_event_id", "event_type", "resource_id", "signature_verified", "payload", "received_at")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TaxDocument)
class TaxDocumentAdmin(admin.ModelAdmin):
    list_display = ("payment", "provider", "kind", "status", "folio", "adjustment_required", "issued_at")
    list_filter = ("provider", "kind", "status", "adjustment_required")
    search_fields = ("payment__external_payment_id", "folio", "external_document_id", "document_token")
    readonly_fields = ("idempotency_key", "attempts", "first_attempt_at", "last_attempt_at", "created_at", "updated_at")
