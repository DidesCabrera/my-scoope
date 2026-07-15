from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

from core.rate_limits import (
    ai_assistant_turn_key,
    ai_assistant_turn_rate,
    login_rate,
    signup_rate,
)


class RateLimitConfigTests(SimpleTestCase):
    @override_settings(RATE_LIMIT_LOGIN="12/m", RATE_LIMIT_SIGNUP="4/m")
    def test_auth_rates_use_settings(self):
        request = SimpleNamespace(user=None)

        self.assertEqual(login_rate(None, request), "12/m")
        self.assertEqual(signup_rate(None, request), "4/m")

    @override_settings(
        RATE_LIMIT_AI_ASSISTANT_TURN_USER="30/h",
        RATE_LIMIT_AI_ASSISTANT_TURN_IP="3/h",
    )
    def test_ai_rate_uses_user_limit_when_authenticated(self):
        request = SimpleNamespace(
            user=SimpleNamespace(is_authenticated=True),
        )

        self.assertEqual(ai_assistant_turn_key(None, request), "user")
        self.assertEqual(ai_assistant_turn_rate(None, request), "30/h")

    @override_settings(
        RATE_LIMIT_AI_ASSISTANT_TURN_USER="30/h",
        RATE_LIMIT_AI_ASSISTANT_TURN_IP="3/h",
    )
    def test_ai_rate_falls_back_to_ip_for_anonymous_requests(self):
        request = SimpleNamespace(
            user=SimpleNamespace(is_authenticated=False),
        )

        self.assertEqual(ai_assistant_turn_key(None, request), "ip")
        self.assertEqual(ai_assistant_turn_rate(None, request), "3/h")
