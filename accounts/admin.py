from django.contrib import admin

from accounts.models import AccountDeletionRecord, AccountPlan, AccountSubscription, CreditLedger, CreditWallet


@admin.register(AccountPlan)
class AccountPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "status",
        "included_monthly_credits",
        "daily_credit_limit",
        "monthly_credit_limit",
        "active_subscriptions",
        "display_order",
        "updated_at",
    )
    list_filter = ("status",)
    search_fields = ("name", "slug", "description")
    readonly_fields = ("active_subscriptions", "created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("display_order", "name")
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "status", "display_order")}),
        (
            "Créditos",
            {"fields": ("included_monthly_credits", "daily_credit_limit", "monthly_credit_limit")},
        ),
        ("Entitlements", {"fields": ("entitlements", "metadata")}),
        ("Auditoría", {"fields": ("active_subscriptions", "created_at", "updated_at")}),
    )

    @admin.display(description="Suscripciones activas")
    def active_subscriptions(self, obj):
        if not obj.pk:
            return 0
        return obj.subscriptions.filter(
            status__in=(AccountSubscription.Status.TRIALING, AccountSubscription.Status.ACTIVE)
        ).count()


@admin.register(AccountSubscription)
class AccountSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "plan",
        "status",
        "source",
        "plan_included_credits",
        "wallet_available_credits",
        "current_period_start",
        "current_period_end",
        "updated_at",
    )
    list_filter = ("status", "source", "plan")
    search_fields = ("user__username", "user__email", "plan__name", "plan__slug")
    readonly_fields = ("plan_included_credits", "wallet_available_credits", "created_at", "updated_at")
    autocomplete_fields = ("user", "plan")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("user", "plan", "status", "source")}),
        ("Periodo", {"fields": ("current_period_start", "current_period_end", "started_at", "ended_at")}),
        ("Créditos", {"fields": ("plan_included_credits", "wallet_available_credits")}),
        ("Metadata", {"fields": ("metadata",)}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Créditos incluidos")
    def plan_included_credits(self, obj):
        return getattr(obj.plan, "included_monthly_credits", 0) or 0

    @admin.display(description="Créditos disponibles")
    def wallet_available_credits(self, obj):
        wallet = getattr(obj.user, "credit_wallet", None)
        if wallet is None:
            return "Sin wallet"
        return wallet.available_credits


@admin.register(CreditWallet)
class CreditWalletAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "balance",
        "reserved_balance",
        "available_credits",
        "period",
        "plan_snapshot_code",
        "is_frozen",
        "ledger_entries_count",
        "updated_at",
    )
    list_filter = ("period", "plan_snapshot_code", "is_frozen")
    search_fields = ("user__username", "user__email", "plan_snapshot_code")
    readonly_fields = ("available_credits", "ledger_entries_count", "created_at", "updated_at")
    autocomplete_fields = ("user",)
    ordering = ("user_id",)
    fieldsets = (
        (None, {"fields": ("user", "period", "plan_snapshot_code")}),
        ("Saldo", {"fields": ("balance", "reserved_balance", "available_credits")}),
        ("Bloqueo operacional", {"fields": ("is_frozen", "frozen_reason", "frozen_at")}),
        ("Auditoría", {"fields": ("ledger_entries_count", "metadata", "created_at", "updated_at")}),
    )

    @admin.display(description="Movimientos")
    def ledger_entries_count(self, obj):
        if not obj.pk:
            return 0
        return obj.ledger_entries.count()


@admin.register(CreditLedger)
class CreditLedgerAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "kind",
        "credits_delta",
        "reserved_delta",
        "balance_after",
        "reserved_balance_after",
        "period",
        "reference_type",
        "reference_id",
    )
    list_filter = ("kind", "period", "reference_type")
    search_fields = ("user__username", "user__email", "reason", "reference_type", "reference_id")
    readonly_fields = (
        "wallet",
        "user",
        "kind",
        "credits_delta",
        "reserved_delta",
        "balance_after",
        "reserved_balance_after",
        "period",
        "plan_snapshot_code",
        "reference_type",
        "reference_id",
        "reason",
        "metadata",
        "created_at",
    )
    autocomplete_fields = ("wallet", "user")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AccountDeletionRecord)
class AccountDeletionRecordAdmin(admin.ModelAdmin):
    list_display = ("public_id", "policy_version", "source", "completed_at")
    readonly_fields = ("public_id", "policy_version", "source", "deleted_counts", "retained_counts", "completed_at")
    ordering = ("-completed_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
