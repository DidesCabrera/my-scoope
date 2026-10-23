from urllib.parse import parse_qs, urlparse

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from notas.application.services.mcp_user_tokens import (
    MCP_SCOPE_PROPOSALS_CREATE,
    MCP_SCOPE_READ,
    validate_mcp_user_token,
)
from notas.application.services.oauth_authorization_codes import (
    OAUTH_CODE_CHALLENGE_METHOD_S256,
)
from notas.domain.models import OAuthClient


@override_settings(MCP_RESOURCE_URL="https://mcp.example.test")
class OAuthTokenEndpointTests(TestCase):
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
        self.code_verifier = "test-code-verifier-123456789"
        self.code_challenge = "HbI_WMU4Dyn8dwHtH9MsCbSM-loQTudStz1c32xWk4s"
        self.resource = "https://mcp.example.test"

    def _authorize_params(self, **overrides):
        params = {
            "client_id": "chatgpt",
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": f"{MCP_SCOPE_READ} {MCP_SCOPE_PROPOSALS_CREATE}",
            "state": "state-123",
            "code_challenge": self.code_challenge,
            "code_challenge_method": OAUTH_CODE_CHALLENGE_METHOD_S256,
            "resource": self.resource,
        }
        params.update(overrides)

        return params

    def _create_authorization_code(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("oauth_authorize_consent"),
            data=self._authorize_params(),
        )

        self.assertEqual(response.status_code, 302)

        redirect = urlparse(response["Location"])
        query = parse_qs(redirect.query)

        return query["code"][0]

    def test_token_endpoint_exchanges_code_for_mcp_user_access_token(self):
        raw_code = self._create_authorization_code()

        response = self.client.post(
            reverse("oauth_token"),
            data={
                "grant_type": "authorization_code",
                "client_id": "chatgpt",
                "code": raw_code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": self.code_verifier,
                "resource": self.resource,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(
            data["access_token"].startswith("mcp_user_"),
        )
        self.assertEqual(
            data["token_type"],
            "Bearer",
        )
        self.assertGreater(
            data["expires_in"],
            0,
        )
        self.assertEqual(
            data["scope"],
            f"{MCP_SCOPE_READ} {MCP_SCOPE_PROPOSALS_CREATE}",
        )

        validation = validate_mcp_user_token(
            data["access_token"],
            required_scopes=[
                MCP_SCOPE_READ,
                MCP_SCOPE_PROPOSALS_CREATE,
            ],
        )

        self.assertTrue(validation.ok)
        self.assertEqual(
            validation.user,
            self.user,
        )

    def test_token_endpoint_rejects_reused_code(self):
        raw_code = self._create_authorization_code()

        first_response = self.client.post(
            reverse("oauth_token"),
            data={
                "grant_type": "authorization_code",
                "client_id": "chatgpt",
                "code": raw_code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": self.code_verifier,
                "resource": self.resource,
            },
        )

        self.assertEqual(first_response.status_code, 200)

        second_response = self.client.post(
            reverse("oauth_token"),
            data={
                "grant_type": "authorization_code",
                "client_id": "chatgpt",
                "code": raw_code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": self.code_verifier,
                "resource": self.resource,
            },
        )

        self.assertEqual(second_response.status_code, 400)

        data = second_response.json()

        self.assertEqual(
            data["error"],
            "invalid_grant",
        )
        self.assertEqual(
            data["details"]["code"],
            "oauth_authorization_code_already_used",
        )

    def test_token_endpoint_requires_matching_resource_without_consuming_code(self):
        raw_code = self._create_authorization_code()
        for resource in ["", "https://other.example.test"]:
            response = self.client.post(
                reverse("oauth_token"),
                data={
                    "grant_type": "authorization_code",
                    "client_id": "chatgpt",
                    "code": raw_code,
                    "redirect_uri": self.redirect_uri,
                    "code_verifier": self.code_verifier,
                    "resource": resource,
                },
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                response.json()["details"]["code"],
                "oauth_authorization_code_resource_mismatch",
            )

        response = self.client.post(
            reverse("oauth_token"),
            data={
                "grant_type": "authorization_code",
                "client_id": "chatgpt",
                "code": raw_code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": self.code_verifier,
                "resource": self.resource,
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_token_endpoint_rejects_wrong_pkce_verifier(self):
        raw_code = self._create_authorization_code()

        response = self.client.post(
            reverse("oauth_token"),
            data={
                "grant_type": "authorization_code",
                "client_id": "chatgpt",
                "code": raw_code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": "wrong-verifier",
                "resource": self.resource,
            },
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()

        self.assertEqual(
            data["error"],
            "invalid_grant",
        )
        self.assertEqual(
            data["details"]["code"],
            "oauth_pkce_verification_failed",
        )

    def test_token_endpoint_rejects_redirect_uri_mismatch(self):
        raw_code = self._create_authorization_code()

        response = self.client.post(
            reverse("oauth_token"),
            data={
                "grant_type": "authorization_code",
                "client_id": "chatgpt",
                "code": raw_code,
                "redirect_uri": "https://chatgpt.com/connector/oauth/other",
                "code_verifier": self.code_verifier,
                "resource": self.resource,
            },
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()

        self.assertEqual(
            data["error"],
            "invalid_grant",
        )
        self.assertEqual(
            data["details"]["code"],
            "oauth_authorization_code_redirect_uri_mismatch",
        )

    def test_token_endpoint_rejects_unknown_client(self):
        raw_code = self._create_authorization_code()

        response = self.client.post(
            reverse("oauth_token"),
            data={
                "grant_type": "authorization_code",
                "client_id": "unknown",
                "code": raw_code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": self.code_verifier,
                "resource": self.resource,
            },
        )

        self.assertEqual(response.status_code, 401)

        data = response.json()

        self.assertEqual(
            data["error"],
            "invalid_client",
        )

    def test_token_endpoint_rejects_missing_code_verifier(self):
        raw_code = self._create_authorization_code()

        response = self.client.post(
            reverse("oauth_token"),
            data={
                "grant_type": "authorization_code",
                "client_id": "chatgpt",
                "code": raw_code,
                "redirect_uri": self.redirect_uri,
            },
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()

        self.assertEqual(
            data["error"],
            "invalid_request",
        )
        self.assertIn(
            "code verifier",
            data["error_description"].lower(),
        )

    def test_token_endpoint_rejects_unsupported_grant_type(self):
        response = self.client.post(
            reverse("oauth_token"),
            data={
                "grant_type": "client_credentials",
                "client_id": "chatgpt",
            },
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()

        self.assertEqual(
            data["error"],
            "unsupported_grant_type",
        )

    def test_token_endpoint_is_csrf_exempt_for_external_clients(self):
        csrf_client = Client(enforce_csrf_checks=True)
        raw_code = self._create_authorization_code()

        response = csrf_client.post(
            reverse("oauth_token"),
            data={
                "grant_type": "authorization_code",
                "client_id": "chatgpt",
                "code": raw_code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": self.code_verifier,
                "resource": self.resource,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(
            data["access_token"].startswith("mcp_user_"),
        )
