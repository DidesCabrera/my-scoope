from __future__ import annotations

import io

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from accounts.models import AccountPlan, AccountSubscription, CreditLedger, CreditWallet
from accounts.services.ai_credits import (
    AI_CREDIT_ADMIN_REFERENCE_TYPE,
    AI_CREDIT_REFERENCE_TYPE,
    account_ai_credit_quota_for_user,
    set_account_ai_credit_freeze,
)
from accounts.services.credits import AccountCreditsFrozen, reserve_account_credits
from ai_assistant.application.credit_reconciliation import ai_credit_reconciliation_summary
from ai_assistant.models import AICreditLedger, AIUsageEvent, AIUserCreditQuota


class AccountAICreditAuthorityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="credit-authority")
        self.plan = AccountPlan.objects.create(
            slug="basic",
            name="Basic",
            status=AccountPlan.Status.ACTIVE,
            included_monthly_credits=20,
            monthly_credit_limit=20,
            daily_credit_limit=10,
        )
        AccountSubscription.objects.create(user=self.user, plan=self.plan)
        self.wallet = CreditWallet.objects.create(
            user=self.user,
            balance=18,
            reserved_balance=0,
            period="2026-08",
            plan_snapshot_code="basic",
        )

    def test_quota_snapshot_is_derived_only_from_account_ledger(self):
        CreditLedger.objects.create(
            wallet=self.wallet,
            user=self.user,
            kind=CreditLedger.Kind.CONSUME,
            credits_delta=-2,
            balance_after=18,
            period="2026-08",
            plan_snapshot_code="basic",
            reference_type=AI_CREDIT_REFERENCE_TYPE,
            reference_id="turn-account",
        )
        AIUserCreditQuota.objects.create(
            user=self.user,
            period="2026-08",
            plan_code="legacy",
            monthly_credit_limit=999,
            credits_used=99,
        )

        quota = account_ai_credit_quota_for_user(self.user, period="2026-08")

        self.assertEqual(quota.plan_code, "basic")
        self.assertEqual(quota.credits_used, 2)
        self.assertEqual(quota.monthly_credit_limit, 20)

    def test_freeze_blocks_reservation_and_writes_account_audit_movement(self):
        wallet, ledger, changed = set_account_ai_credit_freeze(
            wallet_id=self.wallet.pk,
            frozen=True,
            reason="Investigación de uso anómalo",
        )

        self.assertTrue(changed)
        self.assertTrue(wallet.is_frozen)
        self.assertEqual(ledger.reference_type, AI_CREDIT_ADMIN_REFERENCE_TYPE)
        with self.assertRaises(AccountCreditsFrozen):
            reserve_account_credits(
                user=self.user,
                credits=1,
                reference_type=AI_CREDIT_REFERENCE_TYPE,
                reference_id="blocked-turn",
            )

    def test_reconciliation_separates_official_integrity_from_legacy_parity(self):
        event = AIUsageEvent.objects.create(
            user=self.user,
            period="2026-08",
            turn_id="turn-reconciled",
            action_type="assistant.chat",
            status=AIUsageEvent.Status.COMPLETED,
            charged_credits=2,
        )
        CreditLedger.objects.create(
            wallet=self.wallet,
            user=self.user,
            kind=CreditLedger.Kind.CONSUME,
            credits_delta=-2,
            balance_after=18,
            period="2026-08",
            plan_snapshot_code="basic",
            reference_type=AI_CREDIT_REFERENCE_TYPE,
            reference_id=event.turn_id,
        )
        AIUserCreditQuota.objects.create(
            user=self.user,
            period="2026-08",
            plan_code="legacy",
            monthly_credit_limit=20,
            credits_used=1,
        )
        AICreditLedger.objects.create(
            user=self.user,
            usage_event=event,
            period="2026-08",
            plan_code="legacy",
            action_type="assistant.chat",
            credits=1,
        )

        summary = ai_credit_reconciliation_summary(period="2026-08")

        self.assertEqual(summary["account_event_mismatches"], 0)
        self.assertEqual(summary["legacy_account_mismatches"], 1)
        call_command(
            "reconcile_legacy_ai_credits",
            "--period=2026-08",
            "--fail-on-difference",
            stdout=io.StringIO(),
        )
        with self.assertRaises(CommandError):
            call_command(
                "reconcile_legacy_ai_credits",
                "--period=2026-08",
                "--require-legacy-parity",
                stdout=io.StringIO(),
            )
