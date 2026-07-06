from django.test import SimpleTestCase, override_settings

from ai_assistant.application.chat_engines import ChatEngineRequest
from ai_assistant.application.rollout import resolve_ai_llm_rollout, stable_user_bucket


class AIRolloutDecisionTests(SimpleTestCase):
    @override_settings(AI_ASSISTANT_LLM_ROLLOUT_ENABLED=False, AI_ASSISTANT_LLM_ROLLOUT_MODE="all")
    def test_disabled_rollout_blocks_even_when_mode_all(self):
        decision = resolve_ai_llm_rollout(ChatEngineRequest(message="hola", user_id=10))

        self.assertFalse(decision.enabled)
        self.assertEqual(decision.reason, "rollout_disabled")

    @override_settings(AI_ASSISTANT_LLM_ROLLOUT_ENABLED=True, AI_ASSISTANT_LLM_ROLLOUT_MODE="all")
    def test_all_mode_allows_any_authenticated_user_id(self):
        decision = resolve_ai_llm_rollout(ChatEngineRequest(message="hola", user_id=10))

        self.assertTrue(decision.enabled)
        self.assertEqual(decision.reason, "rollout_all")

    @override_settings(
        AI_ASSISTANT_LLM_ROLLOUT_ENABLED=True,
        AI_ASSISTANT_LLM_ROLLOUT_MODE="allowlist",
        AI_ASSISTANT_LLM_ROLLOUT_USER_IDS="3, 7,not-an-id",
    )
    def test_allowlist_mode_allows_only_configured_user_ids(self):
        allowed = resolve_ai_llm_rollout(ChatEngineRequest(message="hola", user_id=7))
        blocked = resolve_ai_llm_rollout(ChatEngineRequest(message="hola", user_id=8))

        self.assertTrue(allowed.enabled)
        self.assertEqual(allowed.reason, "rollout_allowlist")
        self.assertFalse(blocked.enabled)
        self.assertEqual(blocked.reason, "user_not_allowlisted")

    @override_settings(AI_ASSISTANT_LLM_ROLLOUT_ENABLED=True, AI_ASSISTANT_LLM_ROLLOUT_MODE="staff")
    def test_staff_mode_accepts_staff_flag_from_metadata(self):
        decision = resolve_ai_llm_rollout(
            ChatEngineRequest(message="hola", user_id=5, metadata={"is_staff": True})
        )

        self.assertTrue(decision.enabled)
        self.assertEqual(decision.reason, "rollout_staff")

    @override_settings(
        AI_ASSISTANT_LLM_ROLLOUT_ENABLED=True,
        AI_ASSISTANT_LLM_ROLLOUT_MODE="percentage",
        AI_ASSISTANT_LLM_ROLLOUT_PERCENT=100,
        AI_ASSISTANT_LLM_ROLLOUT_STICKY_SALT="test-salt",
    )
    def test_percentage_mode_is_sticky_and_bounded(self):
        first = resolve_ai_llm_rollout(ChatEngineRequest(message="hola", user_id=42))
        second = resolve_ai_llm_rollout(ChatEngineRequest(message="hola", user_id=42))

        self.assertTrue(first.enabled)
        self.assertEqual(first.bucket, second.bucket)
        self.assertEqual(first.bucket, stable_user_bucket(user_id=42, salt="test-salt"))
