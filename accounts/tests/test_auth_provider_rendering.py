import re

from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from allauth.socialaccount.models import SocialApp
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


class AuthProviderRenderingTests(TestCase):
    def test_login_and_signup_render_without_social_apps(self):
        login_response = self.client.get(reverse("account_login"))
        signup_response = self.client.get(reverse("account_signup"))

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(signup_response.status_code, 200)
        self.assertNotContains(login_response, "Continuar con Google")
        self.assertNotContains(signup_response, "Continuar con Google")
        self.assertNotContains(login_response, "Continuar con Apple")
        self.assertNotContains(signup_response, "Continuar con Apple")

    def test_google_option_is_rendered_when_social_app_is_configured(self):
        google_app = SocialApp.objects.create(
            provider="google",
            name="Google",
            client_id="test-client-id",
            secret="test-client-secret",
        )
        google_app.sites.add(Site.objects.get_current())

        response = self.client.get(reverse("account_login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continuar con Google")
        self.assertContains(response, reverse("google_login"))

    def test_apple_option_is_rendered_when_social_app_is_configured(self):
        apple_app = SocialApp.objects.create(
            provider="apple",
            name="Apple",
            client_id="com.myscoope.web",
            secret="TESTKEYID",
            key="TESTTEAMID",
            settings={"certificate_key": "test-private-key"},
        )
        apple_app.sites.add(Site.objects.get_current())

        response = self.client.get(reverse("account_login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continuar con Apple")
        self.assertContains(response, reverse("apple_login"))


class EmailVerificationRenderingTests(TestCase):
    def test_verification_sent_uses_branded_auth_layout(self):
        response = self.client.get(reverse("account_email_verification_sent"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="auth-card auth-card--message"')
        self.assertContains(response, "Verifica tu correo electrónico")
        self.assertNotContains(response, "Menú:")

    def test_email_confirmation_uses_branded_auth_layout(self):
        user = get_user_model().objects.create_user(
            username="confirmation@example.com",
            email="confirmation@example.com",
            password="safe-test-password",
        )
        email_address = EmailAddress.objects.create(
            user=user,
            email=user.email,
            primary=True,
            verified=False,
        )
        confirmation = EmailConfirmationHMAC.create(email_address)

        response = self.client.get(
            reverse("account_confirm_email", kwargs={"key": confirmation.key})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="auth-card auth-card--message"')
        self.assertContains(response, "confirmation@example.com")
        self.assertContains(response, "Confirmar correo")
        self.assertNotContains(response, "Menú:")


class PasswordResetRenderingTests(TestCase):
    def test_password_reset_request_uses_branded_auth_layout(self):
        response = self.client.get(reverse("account_reset_password"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="auth-card auth-card--message"')
        self.assertContains(response, "Recupera tu contraseña")
        self.assertContains(response, "Enviar enlace")

    def test_password_reset_sent_uses_branded_auth_layout(self):
        response = self.client.get(reverse("account_reset_password_done"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Revisa tu correo")
        self.assertContains(response, "Si existe una cuenta asociada")

    def test_password_reset_complete_uses_branded_auth_layout(self):
        response = self.client.get(reverse("account_reset_password_from_key_done"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contraseña actualizada")
        self.assertContains(response, "Iniciar sesión")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_real_password_reset_flow_uses_branded_views(self):
        user = get_user_model().objects.create_user(
            username="password-reset@example.com",
            email="password-reset@example.com",
            password="old-safe-password",
        )
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            primary=True,
            verified=True,
        )

        request_response = self.client.post(
            reverse("account_reset_password"),
            {"email": user.email},
            follow=True,
        )

        self.assertEqual(request_response.status_code, 200)
        self.assertContains(request_response, "Revisa tu correo")
        self.assertEqual(len(mail.outbox), 1)

        reset_url = re.search(r"https?://[^\s]+", mail.outbox[0].body).group(0)
        reset_response = self.client.get(reset_url, follow=True)

        self.assertEqual(reset_response.status_code, 200)
        self.assertContains(reset_response, "Crea una nueva contraseña")

        save_response = self.client.post(
            reset_response.request["PATH_INFO"],
            {
                "password1": "new-safe-password-2026",
                "password2": "new-safe-password-2026",
                "action": "",
            },
            follow=True,
        )

        self.assertEqual(save_response.status_code, 200)
        self.assertContains(save_response, "Contraseña actualizada")
        self.assertTrue(
            self.client.login(
                username=user.email,
                password="new-safe-password-2026",
            )
        )
