import json

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from ai_assistant.application import ExternalLLMOrchestrator
from ai_assistant.application.credits import (
    DjangoAICreditService,
    calculate_event_credits,
    current_period,
    resolve_credit_plan,
)
from ai_assistant.domain import AssistantMessage, AssistantMessageRole, AssistantTurnRequest
from ai_assistant.infrastructure.providers import LLMProviderResponse
from ai_assistant.models import AICreditLedger, AIUsageEvent, AIUserCreditQuota


class ScriptedCreditClient:
    provider_name = "openai"
    model = "gpt-credit-test"

    def __init__(self):
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return LLMProviderResponse(
            provider="openai",
            model=self.model,
            text=json.dumps(
                {
                    "assistant_message": {"content": "Respuesta con créditos."},
                    "intent": {"name": "answer_question", "confidence": 0.8},
                    "requires_human_review": False,
                }
            ),
            response_id="resp-credit-1",
            usage={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
        )


def _turn_request(user, *, action_type="assistant.chat"):
    return AssistantTurnRequest(
        user_message=AssistantMessage(role=AssistantMessageRole.USER, content="Hola"),
        metadata={"tool_user": user, "action_type": action_type},
    )


class AICreditPlanResolutionTests(TestCase):
    @override_settings(
        AI_ASSISTANT_CREDIT_PLANS={
            "default": {"monthly_credit_limit": 0, "daily_credit_limit": 0, "block_on_exhaustion": False},
            "member": {"monthly_credit_limit": 100, "daily_credit_limit": 10, "block_on_exhaustion": True},
        }
    )
    def test_resolves_user_profile_role_to_credit_plan(self):
        user = User.objects.create_user(username="member-user")
        # signals create a default profile/plan in this project; override only the stable role.
        user.profile.role = "member"
        user.profile.plan = None
        user.profile.save(update_fields=["role", "plan"])

        plan = resolve_credit_plan(user)

        self.assertEqual(plan.code, "member")
        self.assertEqual(plan.monthly_credit_limit, 100)
        self.assertEqual(plan.daily_credit_limit, 10)
        self.assertTrue(plan.block_on_exhaustion)


class AICreditCalculationTests(TestCase):
    @override_settings(
        AI_ASSISTANT_USD_PER_AI_CREDIT="0.001",
        AI_ASSISTANT_DEFAULT_CREDITS_PER_TURN=1,
        AI_ASSISTANT_ACTION_CREDIT_MULTIPLIERS={"assistant.create_dailyplan_proposal": "3"},
    )
    def test_calculates_credits_from_cost_and_action_multiplier(self):
        user = User.objects.create_user(username="credit-cost-user")
        event = AIUsageEvent.objects.create(
            user=user,
            period=current_period(),
            action_type="assistant.create_dailyplan_proposal",
            provider="openai",
            model_name="gpt-test",
            estimated_cost_usd="0.0011",
            status=AIUsageEvent.Status.COMPLETED,
        )

        self.assertEqual(calculate_event_credits(event), 6)


class AICreditChargingTests(TestCase):
    @override_settings(
        AI_ASSISTANT_CREDITS_ENABLED=True,
        AI_ASSISTANT_CREDIT_PLANS={
            "default": {"monthly_credit_limit": 0, "daily_credit_limit": 0, "block_on_exhaustion": False},
            "member": {"monthly_credit_limit": 5, "daily_credit_limit": 5, "block_on_exhaustion": True},
        },
        AI_ASSISTANT_DEFAULT_CREDITS_PER_TURN=1,
        AI_ASSISTANT_ACTION_CREDIT_MULTIPLIERS={},
    )
    def test_recorder_charges_completed_usage_event_as_ai_credits(self):
        user = User.objects.create_user(username="credit-charge-user")
        user.profile.role = "member"
        user.profile.plan = None
        user.profile.save(update_fields=["role", "plan"])
        orchestrator = ExternalLLMOrchestrator(llm_client=ScriptedCreditClient())

        response = orchestrator.continue_turn(_turn_request(user))

        self.assertEqual(response.metadata["usage_observability"]["credits"]["charged"], True)
        event = AIUsageEvent.objects.get(user=user)
        quota = AIUserCreditQuota.objects.get(user=user, period=current_period())
        ledger = AICreditLedger.objects.get(user=user, usage_event=event)
        self.assertEqual(event.charged_credits, 1)
        self.assertEqual(event.credit_plan_code, "member")
        self.assertEqual(quota.credits_used, 1)
        self.assertEqual(ledger.credits, 1)

    @override_settings(
        AI_ASSISTANT_CREDITS_ENABLED=True,
        AI_ASSISTANT_CREDIT_PLANS={
            "default": {"monthly_credit_limit": 0, "daily_credit_limit": 0, "block_on_exhaustion": False},
            "member": {"monthly_credit_limit": 1, "daily_credit_limit": 1, "block_on_exhaustion": True},
        },
        AI_ASSISTANT_DEFAULT_CREDITS_PER_TURN=1,
        AI_ASSISTANT_ACTION_CREDIT_MULTIPLIERS={},
    )
    def test_orchestrator_blocks_turn_when_monthly_credit_quota_is_exhausted(self):
        user = User.objects.create_user(username="credit-block-user")
        user.profile.role = "member"
        user.profile.plan = None
        user.profile.save(update_fields=["role", "plan"])
        AIUserCreditQuota.objects.create(
            user=user,
            period=current_period(),
            plan_code="member",
            monthly_credit_limit=1,
            daily_credit_limit=1,
            credits_used=1,
        )
        client = ScriptedCreditClient()
        orchestrator = ExternalLLMOrchestrator(llm_client=client)

        response = orchestrator.continue_turn(_turn_request(user))

        self.assertEqual(client.requests, [])
        self.assertTrue(response.metadata["ai_credit_blocked"])
        self.assertEqual(response.metadata["ai_credit_check"]["reason"], "monthly_credit_limit_exceeded")
        self.assertEqual(response.metadata["usage_observability"]["status"], "blocked")
        self.assertEqual(AIUsageEvent.objects.filter(user=user, status=AIUsageEvent.Status.BLOCKED).count(), 1)
        self.assertEqual(AICreditLedger.objects.filter(user=user).count(), 0)
