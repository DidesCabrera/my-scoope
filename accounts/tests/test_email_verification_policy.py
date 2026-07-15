from types import SimpleNamespace

from django.test import SimpleTestCase

from accounts.adapters import MyScoopeSocialAccountAdapter
from accounts.email_verification import (
    SMTP_EMAIL_BACKEND,
    production_email_verification_default,
    smtp_email_is_configured,
)


class EmailVerificationPolicyTests(SimpleTestCase):
    def test_production_requires_verification_when_smtp_is_configured(self):
        self.assertTrue(smtp_email_is_configured(SMTP_EMAIL_BACKEND, "smtp.resend.com"))
        self.assertEqual(
            production_email_verification_default(SMTP_EMAIL_BACKEND, "smtp.resend.com"),
            "mandatory",
        )

    def test_production_keeps_tolerant_default_without_smtp(self):
        self.assertFalse(smtp_email_is_configured(SMTP_EMAIL_BACKEND, ""))
        self.assertEqual(
            production_email_verification_default(SMTP_EMAIL_BACKEND, ""),
            "none",
        )
        self.assertEqual(
            production_email_verification_default(
                "django.core.mail.backends.console.EmailBackend",
                "",
            ),
            "none",
        )


class GoogleOAuthVerificationPolicyTests(SimpleTestCase):
    def test_google_email_is_trusted_as_verified(self):
        adapter = MyScoopeSocialAccountAdapter()

        self.assertTrue(adapter.is_email_verified(SimpleNamespace(id="google"), "user@test.com"))

    def test_google_can_authenticate_by_verified_email(self):
        adapter = MyScoopeSocialAccountAdapter()
        login = SimpleNamespace(account=SimpleNamespace(provider="google"))

        self.assertTrue(adapter.can_authenticate_by_email(login, "user@test.com"))
