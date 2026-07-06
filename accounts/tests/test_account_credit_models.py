from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import CreditLedger, CreditWallet


class CreditWalletModelTests(TestCase):
    def test_available_credits_subtracts_reserved_balance(self):
        user = get_user_model().objects.create_user(username="wallet-user")
        wallet = CreditWallet.objects.create(user=user, balance=150, reserved_balance=40, period="2026-07")

        self.assertEqual(wallet.available_credits, 110)
        self.assertTrue(wallet.has_reserved_credits)

    def test_available_credits_never_returns_negative(self):
        user = get_user_model().objects.create_user(username="reserved-user")
        wallet = CreditWallet.objects.create(user=user, balance=20, reserved_balance=50)

        self.assertEqual(wallet.available_credits, 0)


class CreditLedgerModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="ledger-user")
        self.wallet = CreditWallet.objects.create(
            user=self.user,
            balance=100,
            reserved_balance=25,
            period="2026-07",
            plan_snapshot_code="starter",
        )

    def test_can_record_signed_credit_movement_with_snapshot(self):
        entry = CreditLedger.objects.create(
            wallet=self.wallet,
            user=self.user,
            kind=CreditLedger.Kind.CONSUME,
            credits_delta=-10,
            reserved_delta=-10,
            balance_after=90,
            reserved_balance_after=15,
            period="2026-07",
            plan_snapshot_code="starter",
            reference_type="ai_usage_event",
            reference_id="42",
            reason="ai_turn_usage",
        )

        self.assertEqual(entry.credits_delta, -10)
        self.assertEqual(entry.reserved_delta, -10)
        self.assertEqual(entry.balance_after, 90)
        self.assertEqual(entry.reserved_balance_after, 15)
        self.assertEqual(entry.reference_type, "ai_usage_event")

    def test_ledger_entry_cannot_be_updated(self):
        entry = CreditLedger.objects.create(
            wallet=self.wallet,
            user=self.user,
            kind=CreditLedger.Kind.GRANT,
            credits_delta=100,
            balance_after=100,
            reserved_balance_after=25,
            period="2026-07",
        )

        entry.reason = "manual_edit_not_allowed"
        with self.assertRaises(ValidationError):
            entry.save()

    def test_ledger_entry_cannot_be_deleted(self):
        entry = CreditLedger.objects.create(
            wallet=self.wallet,
            user=self.user,
            kind=CreditLedger.Kind.RESERVE,
            credits_delta=0,
            reserved_delta=25,
            balance_after=100,
            reserved_balance_after=25,
            period="2026-07",
        )

        with self.assertRaises(ValidationError):
            entry.delete()
