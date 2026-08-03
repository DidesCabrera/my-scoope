from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import AccountPlan, AccountSubscription, CreditWallet
from accounts.services.profile import build_account_credit_display


class AccountCreditDisplayTests(TestCase):
    def setUp(self):
        self.free = AccountPlan.objects.create(
            slug="free",
            name="Free",
            status=AccountPlan.Status.ACTIVE,
            included_monthly_credits=25,
            daily_credit_limit=5,
            monthly_credit_limit=25,
            entitlements={
                "ai_assistant": {
                    "daily_credit_limit": 5,
                    "monthly_credit_limit": 25,
                    "block_on_exhaustion": True,
                }
            },
        )
        self.basic = AccountPlan.objects.create(
            slug="basic",
            name="Basic",
            status=AccountPlan.Status.ACTIVE,
            included_monthly_credits=150,
            daily_credit_limit=30,
            monthly_credit_limit=150,
            entitlements={
                "ai_assistant": {
                    "daily_credit_limit": 30,
                    "monthly_credit_limit": 150,
                    "block_on_exhaustion": True,
                }
            },
        )
        self.user = User.objects.create_user(username="felipe", password="test-pass")

    def test_summary_prefers_account_subscription(self):
        AccountSubscription.objects.update_or_create(
            user=self.user,
            defaults={
                "plan": self.basic,
                "status": AccountSubscription.Status.ACTIVE,
                "source": AccountSubscription.Source.MANUAL,
            },
        )

        summary = build_account_credit_display(self.user)

        self.assertEqual(summary.plan_slug, "basic")
        self.assertEqual(summary.plan_name, "Basic")
        self.assertEqual(summary.available_credits, 150)
        self.assertEqual(summary.monthly_limit_label, "150 créditos/mes")
        self.assertEqual(summary.daily_limit_label, "30 créditos/día")
        self.assertFalse(summary.wallet_exists)
        self.assertEqual(summary.credit_source_label, "Créditos incluidos del plan")

    def test_summary_uses_existing_wallet_when_available(self):
        AccountSubscription.objects.update_or_create(user=self.user, defaults={"plan": self.basic})
        CreditWallet.objects.create(
            user=self.user,
            balance=120,
            reserved_balance=20,
            period="2026-07",
            plan_snapshot_code="basic",
        )

        summary = build_account_credit_display(self.user)

        self.assertEqual(summary.available_credits, 100)
        self.assertEqual(summary.balance, 120)
        self.assertEqual(summary.reserved_credits, 20)
        self.assertTrue(summary.wallet_exists)
        self.assertEqual(summary.credit_source_label, "Wallet comercial actual")

    def test_summary_does_not_create_wallet_by_reading_profile_state(self):
        build_account_credit_display(self.user)

        self.assertFalse(CreditWallet.objects.filter(user=self.user).exists())
