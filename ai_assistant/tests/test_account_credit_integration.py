from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from accounts.models import CreditLedger
from accounts.seed_plans import seed_account_plans
from ai_assistant.application.credits import DjangoAICreditService
from ai_assistant.domain import AssistantMessage, AssistantMessageRole, AssistantTurnRequest
from ai_assistant.infrastructure.providers import LLMMessage, LLMProviderRequest
from ai_assistant.models import AIUsageEvent


@override_settings(AI_ASSISTANT_CREDITS_ENABLED=True, AI_ASSISTANT_DEFAULT_CREDITS_PER_TURN=1)
class AIAccountCreditIntegrationTests(TestCase):
    def setUp(self):
        seed_account_plans()
        self.user = get_user_model().objects.create_user(username="ai-credit-user", password="x")
        self.service = DjangoAICreditService()

    def _turn_request(self, turn_id: str) -> AssistantTurnRequest:
        return AssistantTurnRequest(
            user_message=AssistantMessage(role=AssistantMessageRole.USER, content="Ayúdame con mi plan"),
            metadata={"tool_user": self.user, "turn_id": turn_id, "action_type": "assistant.chat"},
        )

    def _provider_request(self) -> LLMProviderRequest:
        return LLMProviderRequest(messages=[LLMMessage(role="user", content="Hola")], max_output_tokens=100)

    def test_preflight_reserves_account_wallet_credits(self):
        check = self.service.check_turn_allowed(
            request=self._turn_request("turn-reserve"),
            provider_request=self._provider_request(),
            provider="fake",
            model="fake-model",
        )

        self.assertTrue(check.allowed)
        self.assertEqual(check.plan.code, "basic")
        self.assertTrue(check.account_reservation["reserved"])
        wallet = self.user.credit_wallet.__class__.objects.get(user=self.user)
        self.assertEqual(wallet.reserved_balance, check.estimated_credits)
        self.assertEqual(
            CreditLedger.objects.get(reference_id="turn-reserve").kind,
            CreditLedger.Kind.RESERVE,
        )

    def test_completed_usage_consumes_reserved_account_credits(self):
        check = self.service.check_turn_allowed(
            request=self._turn_request("turn-consume"),
            provider_request=self._provider_request(),
            provider="fake",
            model="fake-model",
        )
        event = AIUsageEvent.objects.create(
            user=self.user,
            period="2026-07",
            turn_id="turn-consume",
            action_type="assistant.chat",
            provider="fake",
            model_name="fake-model",
            total_tokens=10,
            status=AIUsageEvent.Status.COMPLETED,
        )

        summary = self.service.charge_usage_event(event)
        self.user.credit_wallet.refresh_from_db()

        self.assertTrue(summary["charged"])
        self.assertEqual(self.user.credit_wallet.reserved_balance, 0)
        self.assertEqual(self.user.credit_wallet.balance, 150 - summary["credits"])
        self.assertEqual(
            list(CreditLedger.objects.filter(reference_id="turn-consume").order_by("id").values_list("kind", flat=True)),
            [CreditLedger.Kind.RESERVE, CreditLedger.Kind.CONSUME],
        )
        self.assertEqual(check.plan.code, summary["plan_code"])

    def test_non_completed_usage_releases_reserved_account_credits(self):
        self.service.check_turn_allowed(
            request=self._turn_request("turn-release"),
            provider_request=self._provider_request(),
            provider="fake",
            model="fake-model",
        )
        event = AIUsageEvent.objects.create(
            user=self.user,
            period="2026-07",
            turn_id="turn-release",
            action_type="assistant.chat",
            status=AIUsageEvent.Status.ERROR,
        )

        summary = self.service.charge_usage_event(event)
        self.user.credit_wallet.refresh_from_db()

        self.assertFalse(summary["charged"])
        self.assertEqual(summary["account_wallet"]["released"], True)
        self.assertEqual(self.user.credit_wallet.reserved_balance, 0)
        self.assertEqual(self.user.credit_wallet.balance, 150)
