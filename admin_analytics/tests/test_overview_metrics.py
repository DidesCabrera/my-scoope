from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription, CreditLedger, CreditWallet
from admin_analytics.selectors.overview import get_overview_metrics
from ai_assistant.models import AIUsageEvent
from notas.domain.model_modules.comparisons import SavedComparison
from notas.domain.model_modules.identity import Profile
from notas.domain.model_modules.proposals import NutritionProposal
from notas.domain.models import DailyPlan, Meal, MealShare, Program


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminAnalyticsOverviewMetricsTests(TestCase):
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

        Profile.objects.update_or_create(
            user=self.member,
            defaults={
                "role": "member",
                "onboarding_completed_at": timezone.now(),
                "onboarding_version": Profile.ONBOARDING_VERSION_NUTRITION_V1,
            },
        )

    def test_selector_returns_executive_overview_metrics(self):
        now = timezone.now()
        plan = AccountPlan.objects.create(slug="basic", name="Basic", status=AccountPlan.Status.ACTIVE)
        AccountSubscription.objects.create(user=self.member, plan=plan, status=AccountSubscription.Status.ACTIVE)
        wallet = CreditWallet.objects.create(user=self.member, balance=100, reserved_balance=12)
        CreditLedger.objects.create(
            wallet=wallet,
            user=self.member,
            kind=CreditLedger.Kind.CONSUME,
            credits_delta=-8,
            reserved_delta=0,
            balance_after=92,
            reserved_balance_after=12,
        )

        meal = Meal.objects.create(name="Meal activa", created_by=self.member, is_draft=False)
        DailyPlan.objects.create(name="Plan activo", created_by=self.member, is_draft=False)
        Program.objects.create(name="Programa activo", created_by=self.other_member, is_draft=False)
        MealShare.objects.create(sender=self.member, recipient_email="friend@example.com", meal=meal)
        SavedComparison.objects.create(owner=self.other_member, kind=SavedComparison.KIND_MEALS, name="Comp", payload=[])

        proposal = NutritionProposal.objects.create(
            created_by=self.member,
            applied_by=self.member,
            status=NutritionProposal.STATUS_APPLIED,
            source=NutritionProposal.SOURCE_AI,
            title="Propuesta IA",
            applied_at=now,
        )
        NutritionProposal.objects.filter(pk=proposal.pk).update(applied_at=now)

        AIUsageEvent.objects.create(
            user=self.member,
            period=now.strftime("%Y-%m"),
            action_type="chat_turn",
            provider="test",
            model_name="fake",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            estimated_cost_usd=Decimal("0.0123"),
            charged_credits=3,
            status=AIUsageEvent.Status.COMPLETED,
        )
        AIUsageEvent.objects.create(
            user=self.member,
            period=now.strftime("%Y-%m"),
            action_type="chat_turn",
            status=AIUsageEvent.Status.ERROR,
        )

        metrics = get_overview_metrics(now=now)

        self.assertEqual(metrics["users"]["total"], 3)
        self.assertEqual(metrics["users"]["onboarding_completed"], 1)
        self.assertEqual(metrics["product_activity"]["weekly_active_nutrition_builders"], 2)
        self.assertEqual(metrics["product_activity"]["meals_7d"], 1)
        self.assertEqual(metrics["product_activity"]["dailyplans_7d"], 1)
        self.assertEqual(metrics["product_activity"]["programs_7d"], 1)
        self.assertEqual(metrics["product_activity"]["shares_7d"], 1)
        self.assertEqual(metrics["ai"]["turns_7d"], 2)
        self.assertEqual(metrics["ai"]["completed_7d"], 1)
        self.assertEqual(metrics["ai"]["error_7d"], 1)
        self.assertEqual(metrics["ai"]["total_tokens_7d"], 150)
        self.assertEqual(metrics["ai"]["charged_credits_7d"], 3)
        self.assertEqual(metrics["accounts"]["active_subscriptions"], 1)
        self.assertEqual(metrics["accounts"]["wallet_reserved_total"], 12)
        self.assertEqual(metrics["accounts"]["credits_consumed_7d"], 8)
        self.assertEqual(metrics["proposals"]["ai_proposals_total"], 1)
        self.assertEqual(metrics["proposals"]["applied_7d"], 1)

    def test_overview_renders_real_metrics_for_staff(self):
        Meal.objects.create(name="Meal visible", created_by=self.member, is_draft=False)
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin_analytics_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Usuarios y activación")
        self.assertContains(response, "Actividad nutricional")
        self.assertContains(response, "AI Assistant")
        self.assertContains(response, "Créditos y cuentas")
        self.assertContains(response, "Weekly Active Nutrition Builders")
        self.assertContains(response, "Meals 7d")
