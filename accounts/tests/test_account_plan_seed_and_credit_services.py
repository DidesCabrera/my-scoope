from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import AccountPlan, CreditLedger
from accounts.seed_plans import seed_account_plans
from accounts.services.credits import (
    consume_account_credit_reservation,
    get_or_create_current_wallet,
    release_account_credit_reservation,
    reserve_account_credits,
    resolve_account_credit_plan_snapshot,
)


class AccountPlanSeedTests(TestCase):
    def test_seed_creates_free_basic_and_pro_plans(self):
        summary = seed_account_plans()

        self.assertEqual(summary["created"], 3)
        self.assertEqual(set(AccountPlan.objects.values_list("slug", flat=True)), {"free", "basic", "pro"})

    def test_seed_is_idempotent(self):
        seed_account_plans()
        summary = seed_account_plans()

        self.assertEqual(summary, {"created": 0, "updated": 0, "unchanged": 3})
        self.assertEqual(AccountPlan.objects.count(), 3)


class AccountCreditWalletServiceTests(TestCase):
    def setUp(self):
        seed_account_plans()
        self.user = get_user_model().objects.create_user(username="wallet-user", password="x")

    def test_wallet_uses_basic_plan_for_legacy_member_profile(self):
        wallet = get_or_create_current_wallet(user=self.user)

        self.assertEqual(wallet.plan_snapshot_code, "basic")
        self.assertEqual(wallet.balance, 150)
        self.assertEqual(wallet.available_credits, 150)

    def test_reserve_consume_and_release_are_audited(self):
        reservation = reserve_account_credits(
            user=self.user,
            credits=3,
            reference_type="ai_assistant_turn",
            reference_id="turn-1",
        )
        wallet = self.user.credit_wallet

        self.assertTrue(reservation["reserved"])
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, 150)
        self.assertEqual(wallet.reserved_balance, 3)
        self.assertEqual(wallet.available_credits, 147)

        consumption = consume_account_credit_reservation(
            user=self.user,
            credits=2,
            reference_type="ai_assistant_turn",
            reference_id="turn-1",
        )
        wallet.refresh_from_db()

        self.assertTrue(consumption["consumed"])
        self.assertEqual(wallet.balance, 148)
        self.assertEqual(wallet.reserved_balance, 0)
        self.assertEqual(
            list(CreditLedger.objects.filter(reference_id="turn-1").order_by("id").values_list("kind", flat=True)),
            [CreditLedger.Kind.RESERVE, CreditLedger.Kind.CONSUME],
        )

        reserve_account_credits(
            user=self.user,
            credits=4,
            reference_type="ai_assistant_turn",
            reference_id="turn-2",
        )
        release = release_account_credit_reservation(
            user=self.user,
            reference_type="ai_assistant_turn",
            reference_id="turn-2",
        )
        wallet.refresh_from_db()

        self.assertTrue(release["released"])
        self.assertEqual(wallet.balance, 148)
        self.assertEqual(wallet.reserved_balance, 0)

    def test_resolves_plan_snapshot_from_seed(self):
        snapshot = resolve_account_credit_plan_snapshot(self.user)

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.slug, "basic")
        self.assertEqual(snapshot.monthly_credit_limit, 150)
        self.assertEqual(snapshot.daily_credit_limit, 30)
