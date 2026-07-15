from django.test import SimpleTestCase, override_settings

from ai_assistant.checks import check_ai_assistant_production_guard


SAFE_CREDIT_PLANS = {
    "free": {
        "monthly_credit_limit": 25,
        "daily_credit_limit": 5,
        "block_on_exhaustion": True,
    },
}

SAFE_LIMITS = {
    "AI_ASSISTANT_MAX_HISTORY_MESSAGES": 8,
    "AI_ASSISTANT_MAX_OUTPUT_TOKENS": 900,
    "AI_ASSISTANT_MAX_TOOL_LOOP_ITERATIONS": 1,
    "AI_ASSISTANT_MAX_INPUT_TOKENS": 6000,
    "AI_ASSISTANT_MAX_CONTEXT_CHARS": 8000,
    "AI_ASSISTANT_MAX_MESSAGE_CHARS": 2000,
    "AI_ASSISTANT_MAX_TOOL_REQUESTS_PER_TURN": 3,
}


class AIProductionGuardCheckTests(SimpleTestCase):
    @override_settings(
        AI_ASSISTANT_CHAT_ENGINE_MODE="llm_production",
        AI_ASSISTANT_LLM_ROLLOUT_ENABLED=True,
        AI_ASSISTANT_LLM_ROLLOUT_MODE="staff",
        AI_ASSISTANT_CREDITS_ENABLED=True,
        AI_ASSISTANT_USD_PER_AI_CREDIT="0.001",
        AI_ASSISTANT_CREDIT_PLANS=SAFE_CREDIT_PLANS,
        **SAFE_LIMITS,
    )
    def test_allows_safe_production_configuration(self):
        self.assertEqual(check_ai_assistant_production_guard(None), [])

    @override_settings(
        AI_ASSISTANT_CHAT_ENGINE_MODE="llm_production",
        AI_ASSISTANT_LLM_ROLLOUT_ENABLED=False,
        AI_ASSISTANT_LLM_ROLLOUT_MODE="off",
        AI_ASSISTANT_CREDITS_ENABLED=False,
        AI_ASSISTANT_USD_PER_AI_CREDIT="0.001",
        AI_ASSISTANT_CREDIT_PLANS=SAFE_CREDIT_PLANS,
        **SAFE_LIMITS,
    )
    def test_blocks_production_engine_without_credit_enforcement(self):
        issues = check_ai_assistant_production_guard(None)

        self.assertIn("ai_assistant.E001", {issue.id for issue in issues})

    @override_settings(
        AI_ASSISTANT_CHAT_ENGINE_MODE="deterministic",
        AI_ASSISTANT_LLM_ROLLOUT_ENABLED=True,
        AI_ASSISTANT_LLM_ROLLOUT_MODE="all",
        AI_ASSISTANT_CREDITS_ENABLED=True,
        AI_ASSISTANT_USD_PER_AI_CREDIT="0",
        AI_ASSISTANT_CREDIT_PLANS=SAFE_CREDIT_PLANS,
        **SAFE_LIMITS,
    )
    def test_active_rollout_requires_positive_credit_price(self):
        issues = check_ai_assistant_production_guard(None)

        self.assertIn("ai_assistant.E002", {issue.id for issue in issues})
