from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from accounts.models import AccountPlan, CreditLedger, CreditWallet
from accounts.services.ai_credits import account_ai_credit_quota_for_user
from accounts.services.credits import reserve_account_credits
from ai_assistant.application.credits import (
    ACCOUNT_CREDIT_REFERENCE_TYPE,
    DjangoAICreditService,
)
from ai_assistant.models import AICreditLedger, AIUsageEvent, AIUserCreditQuota


@override_settings(
    AI_ASSISTANT_CREDITS_ENABLED=True,
    AI_ASSISTANT_DEFAULT_CREDITS_PER_TURN=3,
    AI_ASSISTANT_USD_PER_AI_CREDIT="0.001",
    AI_ASSISTANT_LLM_PRICING_USD_PER_1M_TOKENS={},
)
class AIUsageEventAccountCreditOutcomeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="acc05", password="x")
        self.plan = AccountPlan.objects.create(
            slug="free",
            name="Free",
            status=AccountPlan.Status.ACTIVE,
            included_monthly_credits=10,
            monthly_credit_limit=10,
            daily_credit_limit=5,
            entitlements={
                "ai_assistant": {
                    "monthly_credit_limit": 10,
                    "daily_credit_limit": 5,
                    "block_on_exhaustion": True,
                }
            },
        )

    def test_completed_event_consumes_reserved_account_credits_and_records_outcome(self):
        reserve_account_credits(
            user=self.user,
            credits=3,
            reference_type=ACCOUNT_CREDIT_REFERENCE_TYPE,
            reference_id="turn-acc05-completed",
            reason="test_reservation",
        )
        event = AIUsageEvent.objects.create(
            user=self.user,
            period="2026-07",
            conversation_id="chat-1",
            turn_id="turn-acc05-completed",
            action_type="assistant.chat",
            status=AIUsageEvent.Status.COMPLETED,
            metadata={"surface": "test"},
        )

        summary = DjangoAICreditService().charge_usage_event(event)

        self.assertTrue(summary["charged"])
        self.assertEqual(summary["credits"], 3)
        self.assertTrue(summary["account_wallet"]["consumed"])
        event.refresh_from_db()
        wallet = CreditWallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, 7)
        self.assertEqual(wallet.reserved_balance, 0)
        self.assertEqual(event.credit_plan_code, "free")
        self.assertEqual(event.charged_credits, 3)
        self.assertEqual(event.metadata["surface"], "test")
        outcome = event.metadata["account_credit_outcome"]
        self.assertTrue(outcome["charged"])
        self.assertEqual(outcome["account_wallet"]["credits"], 3)
        self.assertEqual(account_ai_credit_quota_for_user(self.user).credits_used, 3)
        self.assertFalse(AIUserCreditQuota.objects.filter(user=self.user).exists())
        self.assertFalse(AICreditLedger.objects.filter(user=self.user).exists())
        self.assertEqual(
            CreditLedger.objects.filter(
                user=self.user,
                reference_type=ACCOUNT_CREDIT_REFERENCE_TYPE,
                reference_id="turn-acc05-completed",
            ).count(),
            2,
        )

    def test_non_completed_event_releases_reserved_account_credits_and_records_outcome(self):
        reserve_account_credits(
            user=self.user,
            credits=3,
            reference_type=ACCOUNT_CREDIT_REFERENCE_TYPE,
            reference_id="turn-acc05-error",
            reason="test_reservation",
        )
        event = AIUsageEvent.objects.create(
            user=self.user,
            period="2026-07",
            conversation_id="chat-1",
            turn_id="turn-acc05-error",
            action_type="assistant.chat",
            status=AIUsageEvent.Status.ERROR,
            error_type="provider_error",
        )

        summary = DjangoAICreditService().charge_usage_event(event)

        self.assertFalse(summary["charged"])
        self.assertEqual(summary["reason"], "non_completed_turn")
        self.assertTrue(summary["account_wallet"]["released"])
        event.refresh_from_db()
        wallet = CreditWallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, 10)
        self.assertEqual(wallet.reserved_balance, 0)
        self.assertEqual(event.credit_plan_code, "free")
        self.assertEqual(event.charged_credits, 0)
        self.assertFalse(event.metadata["account_credit_outcome"]["charged"])
        self.assertEqual(event.metadata["account_credit_outcome"]["account_wallet"]["credits"], 3)
        self.assertFalse(AICreditLedger.objects.filter(user=self.user, usage_event=event).exists())
        self.assertTrue(
            CreditLedger.objects.filter(
                user=self.user,
                kind=CreditLedger.Kind.RELEASE,
                reference_type=ACCOUNT_CREDIT_REFERENCE_TYPE,
                reference_id="turn-acc05-error",
            ).exists()
        )
