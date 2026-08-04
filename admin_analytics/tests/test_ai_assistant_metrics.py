from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import AccountPlan, AccountSubscription, CreditLedger, CreditWallet
from accounts.services.ai_credits import AI_CREDIT_REFERENCE_TYPE
from admin_analytics.selectors.ai_assistant import get_ai_assistant_metrics
from ai_assistant.application.credits import current_period
from ai_assistant.models import AIUsageEvent
from notas.domain.model_modules.proposals import AiNutritionChat, NutritionProposal


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminAnalyticsAIAssistantMetricsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="password123",
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username="member@example.com",
            email="member@example.com",
            password="password123",
        )
        self.other_member = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="password123",
        )

    def test_selector_returns_ai_assistant_usage_cost_credit_and_outcome_metrics(self):
        period = current_period()
        completed_event = AIUsageEvent.objects.create(
            user=self.member,
            period=period,
            action_type="assistant.chat",
            provider="openai",
            model_name="gpt-test",
            input_tokens=100,
            cached_input_tokens=10,
            output_tokens=50,
            total_tokens=150,
            estimated_cost_usd=Decimal("0.012000"),
            charged_credits=3,
            credit_plan_code="basic",
            status=AIUsageEvent.Status.COMPLETED,
            latency_ms=1200,
            tool_calls_count=2,
        )
        AIUsageEvent.objects.create(
            user=self.other_member,
            period=period,
            action_type="assistant.tool_call",
            provider="openai",
            model_name="gpt-test-mini",
            total_tokens=25,
            estimated_cost_usd=Decimal("0.001000"),
            charged_credits=1,
            credit_plan_code="basic",
            status=AIUsageEvent.Status.BLOCKED,
            error_type="tool_user_required",
            tool_calls_count=1,
        )
        AIUsageEvent.objects.create(
            user=self.member,
            period=period,
            action_type="assistant.chat",
            provider="openai",
            model_name="gpt-test",
            status=AIUsageEvent.Status.ERROR,
            error_type="provider_error",
        )
        plan = AccountPlan.objects.create(
            slug="basic",
            name="Basic",
            status=AccountPlan.Status.ACTIVE,
            included_monthly_credits=10,
            monthly_credit_limit=10,
            daily_credit_limit=4,
        )
        AccountSubscription.objects.create(user=self.member, plan=plan)
        wallet = CreditWallet.objects.create(
            user=self.member,
            period=period,
            plan_snapshot_code="basic",
            balance=7,
            is_frozen=True,
        )
        CreditLedger.objects.create(
            wallet=wallet,
            user=self.member,
            period=period,
            plan_snapshot_code="basic",
            kind=CreditLedger.Kind.CONSUME,
            credits_delta=-3,
            balance_after=7,
            reference_type=AI_CREDIT_REFERENCE_TYPE,
            reference_id=completed_event.turn_id or "analytics-completed-event",
        )
        proposal = NutritionProposal.objects.create(
            created_by=self.member,
            applied_by=self.member,
            status=NutritionProposal.STATUS_APPLIED,
            source=NutritionProposal.SOURCE_AI,
            title="AI proposal",
        )
        NutritionProposal.objects.filter(pk=proposal.pk).update(applied_at=completed_event.created_at)
        AiNutritionChat.objects.create(
            user=self.member,
            title="Chat IA",
            status=AiNutritionChat.STATUS_PROPOSAL_CREATED,
            proposal=proposal,
        )

        metrics = get_ai_assistant_metrics()

        self.assertEqual(metrics["usage"]["events_7d"], 3)
        self.assertEqual(metrics["usage"]["completed_7d"], 1)
        self.assertEqual(metrics["usage"]["error_7d"], 1)
        self.assertEqual(metrics["usage"]["blocked_7d"], 1)
        self.assertEqual(metrics["usage"]["tool_calls_7d"], 3)
        self.assertEqual(metrics["usage"]["total_tokens_7d"], 175)
        self.assertEqual(metrics["usage"]["charged_credits_7d"], 4)
        self.assertEqual(metrics["credits"]["hard_blocked_quotas"], 1)
        self.assertEqual(metrics["credits"]["ledger_entries_7d"], 1)
        self.assertEqual(metrics["outcomes"]["ai_proposals_total"], 1)
        self.assertEqual(metrics["outcomes"]["applied_7d"], 1)
        self.assertEqual(metrics["outcomes"]["proposal_chats"], 1)
        self.assertEqual(metrics["breakdowns"]["by_credit_plan_7d"][0]["credit_plan_code"], "basic")

    def test_ai_assistant_dashboard_is_staff_only_and_renders_metrics(self):
        AIUsageEvent.objects.create(
            user=self.member,
            period=current_period(),
            action_type="assistant.chat",
            provider="openai",
            model_name="gpt-test",
            status=AIUsageEvent.Status.COMPLETED,
            total_tokens=50,
            estimated_cost_usd=Decimal("0.002000"),
            charged_credits=1,
            credit_plan_code="basic",
        )

        response = self.client.get(reverse("admin_analytics_ai_assistant"))
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin_analytics_ai_assistant"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Assistant Analytics")
        self.assertContains(response, "Uso y estado")
        self.assertContains(response, "Tokens y costo")
        self.assertContains(response, "Tools y créditos IA")
        self.assertContains(response, "Outcomes nutricionales")
        self.assertContains(response, "assistant.chat")
