import base64
import hashlib
from urllib.parse import parse_qs, urlparse

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from notas.application.services.oauth_device_sessions import (
    MOBILE_SCOPE_ACCOUNT,
    MOBILE_SCOPE_READ,
    MOBILE_SCOPE_WRITE,
)
from notas.domain.models import OAuthClient, OAuthDeviceSession


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


class OAuthMobileTokenEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="ios-user", password="pass123")
        self.oauth_client = OAuthClient.objects.create(
            client_id="myscoope-ios-endpoint",
            client_name="My Scoope iOS",
            redirect_uris=["https://www.myscoope.com/oauth/mobile/callback"],
            allowed_scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE, MOBILE_SCOPE_ACCOUNT],
        )
        self.verifier = "endpoint-mobile-verifier-with-enough-entropy-123456789"

    def _code(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("oauth_authorize_consent"),
            data={
                "client_id": self.oauth_client.client_id,
                "redirect_uri": "https://www.myscoope.com/oauth/mobile/callback",
                "response_type": "code",
                "scope": f"{MOBILE_SCOPE_READ} {MOBILE_SCOPE_WRITE} {MOBILE_SCOPE_ACCOUNT}",
                "code_challenge": _challenge(self.verifier),
                "code_challenge_method": "S256",
            },
        )
        return parse_qs(urlparse(response["Location"]).query)["code"][0]

    def test_mobile_authorization_code_and_refresh_grants_rotate_tokens(self):
        token_response = self.client.post(
            reverse("oauth_token"),
            data={
                "grant_type": "authorization_code",
                "client_id": self.oauth_client.client_id,
                "code": self._code(),
                "redirect_uri": "https://www.myscoope.com/oauth/mobile/callback",
                "code_verifier": self.verifier,
                "device_id": "8fcafbed-4402-49fb-b93a-a882408eeb09",
                "device_name": "Felipe iPhone",
                "platform": "ios",
            },
        )

        self.assertEqual(token_response.status_code, 200)
        first = token_response.json()
        self.assertTrue(first["refresh_token"].startswith("oauth_refresh_"))
        self.assertTrue(OAuthDeviceSession.objects.filter(public_id=first["device_session_id"]).exists())

        refresh_response = self.client.post(
            reverse("oauth_token"),
            data={
                "grant_type": "refresh_token",
                "client_id": self.oauth_client.client_id,
                "refresh_token": first["refresh_token"],
            },
        )

        self.assertEqual(refresh_response.status_code, 200)
        self.assertNotEqual(refresh_response.json()["refresh_token"], first["refresh_token"])

    def test_mobile_client_cannot_obtain_access_token_without_device_identity(self):
        response = self.client.post(
            reverse("oauth_token"),
            data={
                "grant_type": "authorization_code",
                "client_id": self.oauth_client.client_id,
                "code": self._code(),
                "redirect_uri": "https://www.myscoope.com/oauth/mobile/callback",
                "code_verifier": self.verifier,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["details"]["code"], "oauth_device_id_invalid")
