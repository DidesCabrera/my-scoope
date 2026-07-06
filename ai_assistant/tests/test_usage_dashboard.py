from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ai_assistant.application.credits import current_period
from ai_assistant.application.reports import build_ai_credit_ledger_summary, build_ai_usage_dashboard_report
from ai_assistant.models import AICreditLedger, AIUsageEvent, AIUserCreditQuota


class AIUsageDashboardReportTests(TestCase):
    def test_report_aggregates_usage_by_action_model_user_and_quota_pressure(self):
        user = User.objects.create_user(username="usage-user", email="usage@test.local")
        other = User.objects.create_user(username="other-user", email="other@test.local")
        period = current_period()
        event = AIUsageEvent.objects.create(
            user=user,
            period=period,
            action_type="assistant.ai_nutrition_intake.preview",
            provider="openai",
            model_name="gpt-test",
            input_tokens=100,
            cached_input_tokens=10,
            output_tokens=50,
            total_tokens=150,
            estimated_cost_usd=Decimal("0.001500"),
            charged_credits=2,
            credit_plan_code="member",
            status=AIUsageEvent.Status.COMPLETED,
        )
        AIUsageEvent.objects.create(
            user=other,
            period=period,
            action_type="assistant.ai_nutrition_intake.preview",
            provider="openai",
            model_name="gpt-test",
            total_tokens=10,
            estimated_cost_usd=Decimal("0.000100"),
            credit_plan_code="member",
            status=AIUsageEvent.Status.BLOCKED,
        )
        AIUserCreditQuota.objects.create(
            user=user,
            period=period,
            plan_code="member",
            monthly_credit_limit=10,
            daily_credit_limit=3,
            credits_used=8,
        )
        AICreditLedger.objects.create(
            user=user,
            usage_event=event,
            period=period,
            plan_code="member",
            action_type="assistant.ai_nutrition_intake.preview",
            credits=2,
        )

        report = build_ai_usage_dashboard_report(period=period)

        self.assertEqual(report.kpis.total_events, 2)
        self.assertEqual(report.kpis.completed_events, 1)
        self.assertEqual(report.kpis.blocked_events, 1)
        self.assertEqual(report.kpis.total_tokens, 160)
        self.assertEqual(report.kpis.charged_credits, 2)
        self.assertEqual(report.kpis.active_users, 2)
        self.assertEqual(report.by_action_type[0]["action_type"], "assistant.ai_nutrition_intake.preview")
        self.assertEqual(report.by_action_type[0]["events_count"], 2)
        self.assertEqual(report.by_model[0]["provider"], "openai")
        self.assertEqual(report.by_model[0]["model_name"], "gpt-test")
        self.assertEqual(report.top_users[0]["user__username"], "usage-user")
        self.assertEqual(report.quota_pressure[0]["username"], "usage-user")

    def test_credit_ledger_summary_counts_credits(self):
        user = User.objects.create_user(username="ledger-user")
        period = current_period()
        AICreditLedger.objects.create(
            user=user,
            period=period,
            plan_code="member",
            action_type="assistant.chat",
            credits=4,
        )

        summary = build_ai_credit_ledger_summary(period=period)

        self.assertEqual(summary["entries"], 1)
        self.assertEqual(summary["charged_credits"], 4)


class AIUsageDashboardAdminTests(TestCase):
    def test_staff_admin_can_open_usage_dashboard(self):
        admin_user = User.objects.create_superuser(
            username="admin-user",
            email="admin@test.local",
            password="pw12345",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:ai_assistant_aiusageevent_usage_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Assistant usage dashboard")
        self.assertContains(response, "Estimated cost USD")
