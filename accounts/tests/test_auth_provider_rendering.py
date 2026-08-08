from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.test import TestCase
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
