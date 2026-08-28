from urllib.parse import parse_qs, urlparse

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from notas.application.services.mcp_user_tokens import (
    MCP_SCOPE_PROPOSALS_CREATE,
    MCP_SCOPE_READ,
)
from notas.application.services.oauth_authorization_codes import (
    OAUTH_CODE_CHALLENGE_METHOD_S256,
    hash_oauth_authorization_code,
)
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_ACCOUNT, MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE
from notas.domain.models import OAuthAuthorizationCode, OAuthClient


class OAuthAuthorizeViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@example.com",
            password="pass123",
        )
        self.oauth_client = OAuthClient.objects.create(
            client_id="chatgpt",
            client_name="ChatGPT",
            redirect_uris=[
                "https://chatgpt.com/connector/oauth/callback-test",
            ],
            allowed_scopes=[
                MCP_SCOPE_READ,
                MCP_SCOPE_PROPOSALS_CREATE,
            ],
        )
        self.redirect_uri = "https://chatgpt.com/connector/oauth/callback-test"
        self.code_challenge = "HbI_WMU4Dyn8dwHtH9MsCbSM-loQTudStz1c32xWk4s"

    def _authorize_params(self, **overrides):
        params = {
            "client_id": "chatgpt",
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": f"{MCP_SCOPE_READ} {MCP_SCOPE_PROPOSALS_CREATE}",
            "state": "state-123",
            "code_challenge": self.code_challenge,
            "code_challenge_method": OAUTH_CODE_CHALLENGE_METHOD_S256,
        }
        params.update(overrides)

        return params

    def test_oauth_authorization_server_metadata(self):
        response = self.client.get(
            reverse("oauth_authorization_server_metadata"),
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("issuer", data)
        self.assertIn("authorization_endpoint", data)
        self.assertIn("token_endpoint", data)
        self.assertIn(MCP_SCOPE_READ, data["scopes_supported"])
        self.assertIn(
            MCP_SCOPE_PROPOSALS_CREATE,
            data["scopes_supported"],
        )
        self.assertEqual(
            data["response_types_supported"],
            [
                "code",
            ],
        )
        self.assertEqual(
            data["grant_types_supported"],
            [
                "authorization_code",
                "refresh_token",
            ],
        )
        self.assertIn(MOBILE_SCOPE_READ, data["scopes_supported"])
        self.assertEqual(
            data["code_challenge_methods_supported"],
            [
                OAUTH_CODE_CHALLENGE_METHOD_S256,
            ],
        )

    def test_authorize_requires_login(self):
        response = self.client.get(
            reverse("oauth_authorize"),
            data=self._authorize_params(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response["Location"])

    def test_authorize_renders_consent_for_valid_request(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("oauth_authorize"),
            data=self._authorize_params(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Autorizar ChatGPT")
        self.assertContains(response, "Crear propuestas de dieta")
        self.assertContains(response, MCP_SCOPE_READ)
        self.assertContains(response, MCP_SCOPE_PROPOSALS_CREATE)

    def test_authorize_rejects_unknown_client(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("oauth_authorize"),
            data=self._authorize_params(client_id="unknown"),
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()

        self.assertEqual(
            data["error"]["code"],
            "oauth_client_not_found",
        )

    def test_authorize_rejects_unknown_redirect_uri(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("oauth_authorize"),
            data=self._authorize_params(
                redirect_uri="https://evil.example/callback",
            ),
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()

        self.assertEqual(
            data["error"]["code"],
            "oauth_redirect_uri_not_allowed",
        )

    def test_authorize_rejects_unsupported_response_type(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("oauth_authorize"),
            data=self._authorize_params(response_type="token"),
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()

        self.assertEqual(
            data["error"]["code"],
            "oauth_response_type_not_supported",
        )

    def test_authorize_rejects_unsupported_scope(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("oauth_authorize"),
            data=self._authorize_params(scope="myscoope:admin"),
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()

        self.assertEqual(
            data["error"]["code"],
            "oauth_scope_not_allowed",
        )

    def test_authorize_rejects_missing_code_challenge(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("oauth_authorize"),
            data=self._authorize_params(code_challenge=""),
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()

        self.assertEqual(
            data["error"]["code"],
            "oauth_code_challenge_required",
        )

    def test_authorize_rejects_plain_code_challenge_method(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("oauth_authorize"),
            data=self._authorize_params(code_challenge_method="plain"),
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()

        self.assertEqual(
            data["error"]["code"],
            "oauth_code_challenge_method_not_supported",
        )

    def test_consent_creates_authorization_code_and_redirects_with_state(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("oauth_authorize_consent"),
            data=self._authorize_params(),
        )

        self.assertEqual(response.status_code, 302)

        redirect = urlparse(response["Location"])
        query = parse_qs(redirect.query)

        self.assertEqual(
            f"{redirect.scheme}://{redirect.netloc}{redirect.path}",
            self.redirect_uri,
        )
        self.assertEqual(
            query["state"],
            [
                "state-123",
            ],
        )
        self.assertIn("code", query)

        raw_code = query["code"][0]

        authorization_code = OAuthAuthorizationCode.objects.get(
            code_hash=hash_oauth_authorization_code(raw_code),
        )

        self.assertEqual(
            authorization_code.user,
            self.user,
        )
        self.assertEqual(
            authorization_code.client,
            self.oauth_client,
        )
        self.assertEqual(
            authorization_code.redirect_uri,
            self.redirect_uri,
        )
        self.assertEqual(
            authorization_code.scopes,
            [
                MCP_SCOPE_READ,
                MCP_SCOPE_PROPOSALS_CREATE,
            ],
        )
        self.assertIsNone(
            authorization_code.used_at,
        )

    def test_consent_redirects_to_exact_registered_native_scheme(self):
        mobile_client = OAuthClient.objects.get(client_id="myscoope-ios")
        self.assertEqual(mobile_client.client_name, "My Scoope iOS")
        self.assertTrue(mobile_client.is_active)
        self.assertTrue(mobile_client.allows_redirect_uri("myscoope://oauth/callback"))
        self.assertTrue(
            mobile_client.allows_scopes([MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE, MOBILE_SCOPE_ACCOUNT])
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("oauth_authorize_consent"),
            data=self._authorize_params(
                client_id=mobile_client.client_id,
                redirect_uri="myscoope://oauth/callback",
                scope=f"{MOBILE_SCOPE_READ} {MOBILE_SCOPE_WRITE} {MOBILE_SCOPE_ACCOUNT}",
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("myscoope://oauth/callback?code="))
        self.assertIn("state=state-123", response["Location"])

    def test_consent_requires_login(self):
        response = self.client.post(
            reverse("oauth_authorize_consent"),
            data=self._authorize_params(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response["Location"])


    def test_token_endpoint_rejects_missing_grant_type(self):
        response = self.client.post(
            reverse("oauth_token"),
            data={},
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()

        self.assertEqual(
            data["error"],
            "unsupported_grant_type",
        )
