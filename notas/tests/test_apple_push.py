from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from notas.application.services.notifications.apple_push import (
    _apns_payload,
    _provider_token,
    send_apple_push,
    validate_apple_device_token,
)
from notas.checks import calendarization_push_settings_check


class FakeResponse:
    def __init__(self, status_code=200, reason=""):
        self.status_code = status_code
        self.reason = reason

    def json(self):
        return {"reason": self.reason}


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


@override_settings(
    MYSCOOPE_APNS_ENABLED=True,
    MYSCOOPE_APNS_KEY_ID="KEY123",
    MYSCOOPE_APNS_TEAM_ID="TEAM123",
    MYSCOOPE_APNS_PRIVATE_KEY="private-key",
    MYSCOOPE_APNS_BUNDLE_ID="com.myscoope.app",
    MYSCOOPE_APNS_TIMEOUT_SECONDS=10,
)
class ApplePushTests(SimpleTestCase):
    def test_device_token_is_normalized_and_rejects_non_hex_input(self):
        self.assertEqual(validate_apple_device_token(f"<{('AB' * 32)}>"), "ab" * 32)
        with self.assertRaisesMessage(ValueError, "apns_device_token_invalid"):
            validate_apple_device_token("not-a-device-token")

    def test_payload_contains_only_notification_routing_data(self):
        payload = _apns_payload({"title": "My Scoope", "body": "Tu plan", "url": "/today", "tag": "daily-1"})

        self.assertEqual(payload["aps"]["alert"]["body"], "Tu plan")
        self.assertEqual(payload["myscoope"], {"url": "/today", "tag": "daily-1"})
        self.assertNotIn("user", payload)
        self.assertNotIn("email", payload)

    @patch("notas.application.services.notifications.apple_push.jwt.encode", return_value="signed-provider-token")
    def test_provider_token_is_reused_inside_apple_safe_window(self, encode):
        first = _provider_token(now=1_000)
        second = _provider_token(now=2_000)

        self.assertEqual(first, second)
        encode.assert_called_once()

    @patch("notas.application.services.notifications.apple_push._provider_token", return_value="signed-provider-token")
    def test_sends_http2_contract_to_correct_apns_environment(self, _provider_token):
        client = FakeClient(FakeResponse())
        subscription = SimpleNamespace(device_token="ab" * 32, environment="sandbox")

        result = send_apple_push(
            subscription=subscription,
            payload={"title": "My Scoope", "body": "Tu plan", "tag": "daily-1"},
            client=client,
        )

        self.assertTrue(result.ok)
        url, request = client.calls[0]
        self.assertEqual(url, f"https://api.sandbox.push.apple.com/3/device/{'ab' * 32}")
        self.assertEqual(request["headers"]["apns-topic"], "com.myscoope.app")
        self.assertEqual(request["headers"]["authorization"], "bearer signed-provider-token")

    @patch("notas.application.services.notifications.apple_push._provider_token", return_value="signed-provider-token")
    def test_bad_device_token_expires_subscription(self, _provider_token):
        client = FakeClient(FakeResponse(400, "BadDeviceToken"))
        subscription = SimpleNamespace(device_token="ab" * 32, environment="production")

        result = send_apple_push(subscription=subscription, payload={}, client=client)

        self.assertFalse(result.ok)
        self.assertTrue(result.expired)
        self.assertEqual(result.failure_code, "apns_BadDeviceToken")


class ApplePushConfigurationTests(SimpleTestCase):
    @override_settings(
        MYSCOOPE_APNS_ENABLED=True,
        MYSCOOPE_APNS_KEY_ID="",
        MYSCOOPE_APNS_TEAM_ID="",
        MYSCOOPE_APNS_PRIVATE_KEY="",
        MYSCOOPE_APNS_BUNDLE_ID="com.myscoope.app",
    )
    def test_enabled_apns_fails_closed_without_provider_credentials(self):
        errors = calendarization_push_settings_check(None)

        self.assertEqual([error.id for error in errors], ["notas.E002"])
        self.assertIn("MYSCOOPE_APNS_PRIVATE_KEY", errors[0].hint)
