from __future__ import annotations

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from ai_assistant.models import AIUsageEvent


class PostToolFollowupHealthCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="post-tool-health")

    def _event(self, *, status: str, error_type: str = "") -> AIUsageEvent:
        return AIUsageEvent.objects.create(
            user=self.user,
            period="2026-07",
            action_type="assistant.tool_call",
            provider="openai",
            model_name="gpt-test",
            status=status,
            error_type=error_type,
            tool_calls_count=1,
        )

    def test_passes_when_recent_tool_turns_are_provider_written(self):
        self._event(status=AIUsageEvent.Status.COMPLETED)
        stdout = StringIO()

        call_command(
            "check_post_tool_followup_health",
            minutes=60,
            max_degraded=0,
            stdout=stdout,
        )

        self.assertIn("healthy=1", stdout.getvalue())
        self.assertIn("degraded=0", stdout.getvalue())
        self.assertIn("PASS", stdout.getvalue())

    def test_fails_when_a_recent_tool_turn_is_degraded(self):
        self._event(
            status=AIUsageEvent.Status.DEGRADED,
            error_type="tool_followup_LLMProviderRequestError",
        )

        with self.assertRaisesMessage(CommandError, "threshold exceeded"):
            call_command(
                "check_post_tool_followup_health",
                minutes=60,
                max_degraded=0,
                stdout=StringIO(),
            )

    def test_allows_an_explicit_small_threshold(self):
        self._event(status=AIUsageEvent.Status.DEGRADED)
        stdout = StringIO()

        call_command(
            "check_post_tool_followup_health",
            minutes=60,
            max_degraded=1,
            stdout=stdout,
        )

        self.assertIn("degraded=1", stdout.getvalue())
        self.assertIn("PASS", stdout.getvalue())
