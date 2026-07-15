from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

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
        AIUsageEvent.objects.create(
            user=user,
            period=period,
            action_type="assistant.ai_nutrition_intake.preview",
            provider="openai",
            model_name="gpt-test",
            total_tokens=5,
            estimated_cost_usd=Decimal("0.000050"),
            credit_plan_code="member",
            status=AIUsageEvent.Status.DEGRADED,
            error_type="tool_followup_LLMProviderRequestError",
            metadata={"post_tool_degradation": {"degraded": True}},
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

        self.assertEqual(report.kpis.total_events, 3)
        self.assertEqual(report.kpis.completed_events, 1)
        self.assertEqual(report.kpis.degraded_events, 1)
        self.assertEqual(report.kpis.blocked_events, 1)
        self.assertEqual(report.kpis.total_tokens, 165)
        self.assertEqual(report.kpis.charged_credits, 2)
        self.assertEqual(report.kpis.active_users, 2)
        self.assertEqual(report.by_action_type[0]["action_type"], "assistant.ai_nutrition_intake.preview")
        self.assertEqual(report.by_action_type[0]["events_count"], 3)
        self.assertEqual(report.by_action_type[0]["degraded_events"], 1)
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
