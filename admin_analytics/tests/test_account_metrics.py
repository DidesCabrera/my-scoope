from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import AccountPlan, AccountSubscription, CreditLedger, CreditWallet
from admin_analytics.selectors.accounts import get_account_metrics


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminAnalyticsAccountMetricsTests(TestCase):
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

    def test_selector_returns_account_commercial_metrics(self):
        free = AccountPlan.objects.create(
            slug="free",
            name="Free",
            status=AccountPlan.Status.ACTIVE,
            included_monthly_credits=100,
            daily_credit_limit=10,
            monthly_credit_limit=100,
        )
        pro = AccountPlan.objects.create(
            slug="pro",
            name="Pro",
            status=AccountPlan.Status.ACTIVE,
            included_monthly_credits=1000,
            monthly_credit_limit=2000,
        )
        AccountPlan.objects.create(slug="draft", name="Draft", status=AccountPlan.Status.DRAFT)

        AccountSubscription.objects.create(user=self.member, plan=free, status=AccountSubscription.Status.ACTIVE)
        AccountSubscription.objects.create(user=self.other_member, plan=pro, status=AccountSubscription.Status.TRIALING)

        wallet = CreditWallet.objects.create(
            user=self.member,
            balance=100,
            reserved_balance=15,
            period="2026-07",
            plan_snapshot_code="free",
        )
        CreditWallet.objects.create(user=self.other_member, balance=50, reserved_balance=0, period="2026-07")

        CreditLedger.objects.create(
            wallet=wallet,
            user=self.member,
            kind=CreditLedger.Kind.GRANT,
            credits_delta=100,
            reserved_delta=0,
            balance_after=100,
            reserved_balance_after=0,
        )
        CreditLedger.objects.create(
            wallet=wallet,
            user=self.member,
            kind=CreditLedger.Kind.RESERVE,
            credits_delta=0,
            reserved_delta=15,
            balance_after=100,
            reserved_balance_after=15,
        )
        CreditLedger.objects.create(
            wallet=wallet,
            user=self.member,
            kind=CreditLedger.Kind.CONSUME,
            credits_delta=-20,
            reserved_delta=-10,
            balance_after=80,
            reserved_balance_after=5,
        )

        metrics = get_account_metrics()

        self.assertEqual(metrics["plans"]["total"], 3)
        self.assertEqual(metrics["plans"]["active"], 2)
        self.assertEqual(metrics["subscriptions"]["active"], 2)
        self.assertEqual(metrics["wallets"]["total"], 2)
        self.assertEqual(metrics["wallets"]["balance_total"], 150)
        self.assertEqual(metrics["wallets"]["reserved_total"], 15)
        self.assertEqual(metrics["wallets"]["available_total"], 135)
        self.assertEqual(metrics["ledger"]["entries_7d"], 3)
        self.assertEqual(metrics["ledger"]["credits_granted_7d"], 100)
        self.assertEqual(metrics["ledger"]["credits_consumed_7d"], 20)
        self.assertEqual(metrics["ledger"]["credits_reserved_7d"], 15)
        self.assertEqual(len(metrics["subscriptions"]["active_by_plan"]), 2)

    def test_accounts_dashboard_is_staff_only_and_renders_metrics(self):
        plan = AccountPlan.objects.create(slug="basic", name="Basic", status=AccountPlan.Status.ACTIVE)
        AccountSubscription.objects.create(user=self.member, plan=plan, status=AccountSubscription.Status.ACTIVE)
        CreditWallet.objects.create(user=self.member, balance=30, reserved_balance=3)

        response = self.client.get(reverse("admin_analytics_accounts"))
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin_analytics_accounts"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accounts Analytics")
        self.assertContains(response, "Planes comerciales")
        self.assertContains(response, "Suscripciones")
        self.assertContains(response, "Wallets")
        self.assertContains(response, "Ledger de créditos")
        self.assertContains(response, "Basic")
