from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path

from ai_assistant.application.reports import build_ai_usage_dashboard_report
from ai_assistant.models import AICreditLedger, AIUsageEvent, AIUserCreditQuota


@admin.register(AIUsageEvent)
class AIUsageEventAdmin(admin.ModelAdmin):
    change_list_template = "admin/ai_assistant/aiusageevent/change_list.html"
    list_display = (
        "created_at",
        "user",
        "action_type",
        "provider",
        "model_name",
        "total_tokens",
        "estimated_cost_usd",
        "charged_credits",
        "credit_plan_code",
        "status",
    )
    list_filter = ("status", "provider", "model_name", "action_type", "period", "credit_plan_code")
    search_fields = ("action_type", "provider", "model_name", "conversation_id", "turn_id", "user__username")
    date_hierarchy = "created_at"
    readonly_fields = (
        "created_at",
        "period",
        "user",
        "conversation_id",
        "turn_id",
        "action_type",
        "provider",
        "model_name",
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "total_tokens",
        "estimated_cost_usd",
        "charged_credits",
        "credit_plan_code",
        "status",
        "error_type",
        "latency_ms",
        "tool_calls_count",
        "usage_payload",
        "metadata",
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "usage-dashboard/",
                self.admin_site.admin_view(self.usage_dashboard_view),
                name="ai_assistant_aiusageevent_usage_dashboard",
            ),
        ]
        return custom_urls + urls

    def usage_dashboard_view(self, request):
        period = request.GET.get("period") or None
        report = build_ai_usage_dashboard_report(period=period)
        context = {
            **self.admin_site.each_context(request),
            "title": "AI Assistant usage dashboard",
            "opts": self.model._meta,
            "report": report,
            "period": report.period,
        }
        return TemplateResponse(
            request,
            "admin/ai_assistant/aiusageevent/usage_dashboard.html",
            context,
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AIUserCreditQuota)
class AIUserCreditQuotaAdmin(admin.ModelAdmin):
    list_display = (
        "period",
        "user",
        "plan_code",
        "credits_used",
        "monthly_credit_limit",
        "daily_credit_limit",
        "hard_blocked",
        "updated_at",
    )
    list_filter = ("period", "plan_code", "hard_blocked")
    search_fields = ("user__username", "user__email", "plan_code")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AICreditLedger)
class AICreditLedgerAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "period",
        "plan_code",
        "action_type",
        "credits",
        "kind",
        "reason",
    )
    list_filter = ("period", "plan_code", "action_type", "kind")
    search_fields = ("user__username", "user__email", "action_type", "reason")
    date_hierarchy = "created_at"
    readonly_fields = (
        "created_at",
        "user",
        "usage_event",
        "period",
        "plan_code",
        "action_type",
        "kind",
        "credits",
        "reason",
        "metadata",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
