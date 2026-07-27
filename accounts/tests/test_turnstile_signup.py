from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from email_delivery.models import EmailDeliveryAttempt


@override_settings(
    ACCOUNT_EMAIL_VERIFICATION="mandatory",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    TURNSTILE_ENABLED=True,
    TURNSTILE_SITE_KEY="test-site-key",
    TURNSTILE_SECRET_KEY="test-secret-key",
    TURNSTILE_EXPECTED_ACTION="signup",
    TURNSTILE_EXPECTED_HOSTNAME="testserver",
    RATE_LIMIT_SIGNUP="100/10m",
    RATE_LIMIT_SIGNUP_IP_DAILY="100/d",
    RATE_LIMIT_SIGNUP_EMAIL_DAILY="100/d",
)
class TurnstileSignupTests(TestCase):
    def _response(self, payload):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload
        return response

    @patch("accounts.turnstile.requests.post")
    def test_invalid_token_creates_no_user_and_sends_no_email(self, post):
        post.return_value = self._response({"success": False})

        response = self.client.post(
            reverse("account_signup"),
            {
                "email": "blocked@example.com",
                "password1": "Strong-passphrase-2026",
                "password2": "Strong-passphrase-2026",
                "cf-turnstile-response": "invalid",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(email="blocked@example.com").exists()
        )
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, "No pudimos validar")

    @patch("accounts.turnstile.requests.post")
    def test_valid_token_creates_pending_account_and_audits_email(self, post):
        post.return_value = self._response(
            {
                "success": True,
                "action": "signup",
                "hostname": "testserver",
            }
        )

        response = self.client.post(
            reverse("account_signup"),
            {
                "email": "verified-later@example.com",
                "password1": "Strong-passphrase-2026",
                "password2": "Strong-passphrase-2026",
                "cf-turnstile-response": "valid",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            get_user_model().objects.filter(
                email="verified-later@example.com"
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(
            EmailDeliveryAttempt.objects.filter(
                category=EmailDeliveryAttempt.CATEGORY_EMAIL_VERIFICATION,
                status=EmailDeliveryAttempt.STATUS_SENT,
                recipient_email="verified-later@example.com",
            ).exists()
        )

    @patch("accounts.turnstile.requests.post")
    def test_wrong_action_is_rejected(self, post):
        post.return_value = self._response(
            {
                "success": True,
                "action": "login",
                "hostname": "testserver",
            }
        )

        response = self.client.post(
            reverse("account_signup"),
            {
                "email": "wrong-action@example.com",
                "password1": "Strong-passphrase-2026",
                "password2": "Strong-passphrase-2026",
                "cf-turnstile-response": "valid",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(
                email="wrong-action@example.com"
            ).exists()
        )

    @override_settings(
        TURNSTILE_EXPECTED_HOSTNAME="testserver,www.testserver"
    )
    @patch("accounts.turnstile.requests.post")
    def test_hostname_allowlist_accepts_configured_alias(self, post):
        post.return_value = self._response(
            {
                "success": True,
                "action": "signup",
                "hostname": "www.testserver",
            }
        )

        response = self.client.post(
            reverse("account_signup"),
            {
                "email": "hostname-alias@example.com",
                "password1": "Strong-passphrase-2026",
                "password2": "Strong-passphrase-2026",
                "cf-turnstile-response": "valid",
            },
        )

        self.assertEqual(response.status_code, 302)


@override_settings(
    ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class UnknownAccountEmailTests(TestCase):
    def test_password_reset_for_unknown_email_sends_nothing(self):
        response = self.client.post(
            reverse("account_reset_password"),
            {"email": "does-not-exist@example.com"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(
            EmailDeliveryAttempt.objects.filter(
                recipient_email="does-not-exist@example.com"
            ).exists()
        )
