import json

from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    ACCOUNT_EMAIL_VERIFICATION="mandatory",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    TURNSTILE_ENABLED=False,
)
class MobileEmailConfirmationTests(TestCase):
    def test_mobile_signup_marks_confirmation_link(self):
        mobile_return = (
            f'{reverse("oauth_authorize")}?client_id=myscoope-ios'
            "&redirect_uri=myscoope%3A%2F%2Foauth%2Fcallback"
            "&response_type=code&scope=mobile%3Aread"
        )
        response = self.client.post(
            reverse("account_signup"),
            {
                "email": "mobile-signup@example.com",
                "password1": "Strong-passphrase-2026",
                "password2": "Strong-passphrase-2026",
                "next": mobile_return,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/mobile/confirm-email/", mail.outbox[0].body)

    def test_web_signup_keeps_web_confirmation_link(self):
        response = self.client.post(
            reverse("account_signup"),
            {
                "email": "web-signup@example.com",
                "password1": "Strong-passphrase-2026",
                "password2": "Strong-passphrase-2026",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/confirm-email/", mail.outbox[0].body)
        self.assertNotIn("/mobile/confirm-email/", mail.outbox[0].body)

    def test_confirmation_returns_to_app_and_web_confirmation_stays_on_web(self):
        for source in ("mobile", "web"):
            with self.subTest(source=source):
                user = get_user_model().objects.create_user(
                    username=f"{source}@example.com",
                    email=f"{source}@example.com",
                    password="Strong-passphrase-2026",
                )
                email_address = EmailAddress.objects.create(
                    user=user, email=user.email, primary=True, verified=False
                )
                confirmation = EmailConfirmationHMAC.create(email_address)
                route_name = "mobile_confirm_email" if source == "mobile" else "account_confirm_email"
                url = reverse(route_name, kwargs={"key": confirmation.key})
                page = self.client.get(url)
                self.assertEqual(page.status_code, 200)

                response = self.client.post(url)
                email_address.refresh_from_db()
                self.assertTrue(email_address.verified)
                if source == "mobile":
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, "myscoope://login?emailConfirmed=1")
                else:
                    self.assertEqual(response.status_code, 302)
                    self.assertNotIn("myscoope://login", response["Location"])

    def test_mobile_api_confirms_without_signing_in(self):
        user = get_user_model().objects.create_user(
            username="api-confirm@example.com",
            email="api-confirm@example.com",
            password="Strong-passphrase-2026",
        )
        email_address = EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=False
        )
        key = EmailConfirmationHMAC.create(email_address).key

        response = self.client.post(
            "/api/v1/auth/confirm-email",
            data=json.dumps({"key": key}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        email_address.refresh_from_db()
        self.assertTrue(email_address.verified)
        self.assertNotIn("_auth_user_id", self.client.session)

        replay = self.client.post(
            "/api/v1/auth/confirm-email",
            data=json.dumps({"key": key}),
            content_type="application/json",
        )
        self.assertEqual(replay.status_code, 400)
