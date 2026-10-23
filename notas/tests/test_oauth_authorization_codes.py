from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from notas.application.services.mcp_user_tokens import (
    MCP_SCOPE_PROPOSALS_CREATE,
    MCP_SCOPE_READ,
)
from notas.application.services.oauth_authorization_codes import (
    OAUTH_CODE_CHALLENGE_METHOD_S256,
    create_oauth_authorization_code,
    hash_oauth_authorization_code,
    normalize_oauth_scopes,
    validate_oauth_authorization_code,
    validate_pkce_s256,
)
from notas.domain.models import OAuthAuthorizationCode, OAuthClient


@override_settings(MCP_RESOURCE_URL="https://mcp.example.test")
class OAuthAuthorizationCodeServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@example.com",
            password="pass123",
        )
        self.client_app = OAuthClient.objects.create(
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

    def test_normalize_oauth_scopes_from_string(self):
        self.assertEqual(
            normalize_oauth_scopes(
                f"{MCP_SCOPE_READ} {MCP_SCOPE_PROPOSALS_CREATE} {MCP_SCOPE_READ}"
            ),
            [
                MCP_SCOPE_READ,
                MCP_SCOPE_PROPOSALS_CREATE,
            ],
        )

    def test_validate_pkce_s256_accepts_matching_verifier(self):
        self.assertTrue(
            validate_pkce_s256(
                code_verifier=self.code_verifier,
                code_challenge=self.code_challenge,
            )
        )

    def test_validate_pkce_s256_rejects_wrong_verifier(self):
        self.assertFalse(
            validate_pkce_s256(
                code_verifier="wrong-verifier",
                code_challenge=self.code_challenge,
            )
        )

    def test_create_oauth_authorization_code_stores_hash_not_raw_code(self):
        created = create_oauth_authorization_code(
            user=self.user,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            scopes=[
                MCP_SCOPE_READ,
                MCP_SCOPE_PROPOSALS_CREATE,
            ],
            code_challenge=self.code_challenge,
        )

        self.assertTrue(
            created.raw_code.startswith("oauth_code_"),
        )
        self.assertEqual(
            created.authorization_code.code_hash,
            hash_oauth_authorization_code(created.raw_code),
        )
        self.assertNotEqual(
            created.authorization_code.code_hash,
            created.raw_code,
        )
        self.assertEqual(
            created.authorization_code.user,
            self.user,
        )
        self.assertEqual(
            created.authorization_code.client,
            self.client_app,
        )
        self.assertEqual(
            created.authorization_code.redirect_uri,
            self.redirect_uri,
        )
        self.assertEqual(
            created.authorization_code.scopes,
            [
                MCP_SCOPE_READ,
                MCP_SCOPE_PROPOSALS_CREATE,
            ],
        )
        self.assertEqual(
            created.authorization_code.code_challenge_method,
            OAUTH_CODE_CHALLENGE_METHOD_S256,
        )

    def test_create_oauth_authorization_code_rejects_inactive_client(self):
        self.client_app.is_active = False
        self.client_app.save(update_fields=["is_active"])

        with self.assertRaisesMessage(
            ValueError,
            "oauth_client_inactive",
        ):
            create_oauth_authorization_code(
                user=self.user,
                client=self.client_app,
                redirect_uri=self.redirect_uri,
                scopes=[MCP_SCOPE_READ],
                code_challenge=self.code_challenge,
            )

    def test_create_oauth_authorization_code_rejects_unknown_redirect_uri(self):
        with self.assertRaisesMessage(
            ValueError,
            "oauth_redirect_uri_not_allowed",
        ):
            create_oauth_authorization_code(
                user=self.user,
                client=self.client_app,
                redirect_uri="https://evil.example/callback",
                scopes=[MCP_SCOPE_READ],
                code_challenge=self.code_challenge,
            )

    def test_create_oauth_authorization_code_rejects_unknown_scope(self):
        with self.assertRaisesMessage(
            ValueError,
            "oauth_scope_not_allowed",
        ):
            create_oauth_authorization_code(
                user=self.user,
                client=self.client_app,
                redirect_uri=self.redirect_uri,
                scopes=["myscoope:admin"],
                code_challenge=self.code_challenge,
            )

    def test_create_oauth_authorization_code_rejects_unsupported_challenge_method(self):
        with self.assertRaisesMessage(
            ValueError,
            "oauth_code_challenge_method_not_supported",
        ):
            create_oauth_authorization_code(
                user=self.user,
                client=self.client_app,
                redirect_uri=self.redirect_uri,
                scopes=[MCP_SCOPE_READ],
                code_challenge=self.code_challenge,
                code_challenge_method="plain",
            )

    def test_create_oauth_authorization_code_rejects_missing_code_challenge(self):
        with self.assertRaisesMessage(
            ValueError,
            "oauth_code_challenge_required",
        ):
            create_oauth_authorization_code(
                user=self.user,
                client=self.client_app,
                redirect_uri=self.redirect_uri,
                scopes=[MCP_SCOPE_READ],
                code_challenge="",
            )

    def test_validate_oauth_authorization_code_accepts_valid_code_and_marks_used(self):
        created = create_oauth_authorization_code(
            user=self.user,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            scopes=[MCP_SCOPE_READ],
            code_challenge=self.code_challenge,
        )

        result = validate_oauth_authorization_code(
            raw_code=created.raw_code,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            code_verifier=self.code_verifier,
        )

        self.assertTrue(result.ok)
        self.assertEqual(
            result.user,
            self.user,
        )
        self.assertEqual(
            result.client,
            self.client_app,
        )

        created.authorization_code.refresh_from_db()

        self.assertIsNotNone(
            created.authorization_code.used_at,
        )

    def test_validate_oauth_authorization_code_rejects_missing_code(self):
        result = validate_oauth_authorization_code(
            raw_code="",
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            code_verifier=self.code_verifier,
        )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.error.code,
            "oauth_authorization_code_missing",
        )

    def test_validate_oauth_authorization_code_rejects_unknown_code(self):
        result = validate_oauth_authorization_code(
            raw_code="oauth_code_unknown",
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            code_verifier=self.code_verifier,
        )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.error.code,
            "oauth_authorization_code_invalid",
        )

    def test_validate_oauth_authorization_code_rejects_client_mismatch(self):
        created = create_oauth_authorization_code(
            user=self.user,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            scopes=[MCP_SCOPE_READ],
            code_challenge=self.code_challenge,
        )
        other_client = OAuthClient.objects.create(
            client_id="other-client",
            client_name="Other Client",
            redirect_uris=[
                self.redirect_uri,
            ],
            allowed_scopes=[
                MCP_SCOPE_READ,
            ],
        )

        result = validate_oauth_authorization_code(
            raw_code=created.raw_code,
            client=other_client,
            redirect_uri=self.redirect_uri,
            code_verifier=self.code_verifier,
        )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.error.code,
            "oauth_authorization_code_client_mismatch",
        )

    def test_validate_oauth_authorization_code_rejects_redirect_uri_mismatch(self):
        created = create_oauth_authorization_code(
            user=self.user,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            scopes=[MCP_SCOPE_READ],
            code_challenge=self.code_challenge,
        )

        result = validate_oauth_authorization_code(
            raw_code=created.raw_code,
            client=self.client_app,
            redirect_uri="https://chatgpt.com/connector/oauth/other",
            code_verifier=self.code_verifier,
        )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.error.code,
            "oauth_authorization_code_redirect_uri_mismatch",
        )

    def test_validate_oauth_authorization_code_rejects_reused_code(self):
        created = create_oauth_authorization_code(
            user=self.user,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            scopes=[MCP_SCOPE_READ],
            code_challenge=self.code_challenge,
        )

        first_result = validate_oauth_authorization_code(
            raw_code=created.raw_code,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            code_verifier=self.code_verifier,
        )

        self.assertTrue(first_result.ok)

        second_result = validate_oauth_authorization_code(
            raw_code=created.raw_code,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            code_verifier=self.code_verifier,
        )

        self.assertFalse(second_result.ok)
        self.assertEqual(
            second_result.error.code,
            "oauth_authorization_code_already_used",
        )

    def test_validate_oauth_authorization_code_rejects_expired_code(self):
        created = create_oauth_authorization_code(
            user=self.user,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            scopes=[MCP_SCOPE_READ],
            code_challenge=self.code_challenge,
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        result = validate_oauth_authorization_code(
            raw_code=created.raw_code,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            code_verifier=self.code_verifier,
        )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.error.code,
            "oauth_authorization_code_expired",
        )

    def test_validate_oauth_authorization_code_rejects_inactive_client(self):
        created = create_oauth_authorization_code(
            user=self.user,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            scopes=[MCP_SCOPE_READ],
            code_challenge=self.code_challenge,
        )
        self.client_app.is_active = False
        self.client_app.save(update_fields=["is_active"])

        result = validate_oauth_authorization_code(
            raw_code=created.raw_code,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            code_verifier=self.code_verifier,
        )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.error.code,
            "oauth_client_inactive",
        )

    def test_validate_oauth_authorization_code_rejects_inactive_user(self):
        created = create_oauth_authorization_code(
            user=self.user,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            scopes=[MCP_SCOPE_READ],
            code_challenge=self.code_challenge,
        )
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        result = validate_oauth_authorization_code(
            raw_code=created.raw_code,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            code_verifier=self.code_verifier,
        )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.error.code,
            "oauth_user_inactive",
        )

    def test_validate_oauth_authorization_code_rejects_wrong_pkce_verifier(self):
        created = create_oauth_authorization_code(
            user=self.user,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            scopes=[MCP_SCOPE_READ],
            code_challenge=self.code_challenge,
        )

        result = validate_oauth_authorization_code(
            raw_code=created.raw_code,
            client=self.client_app,
            redirect_uri=self.redirect_uri,
            code_verifier="wrong-verifier",
        )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.error.code,
            "oauth_pkce_verification_failed",
        )

    def test_oauth_client_helpers(self):
        self.assertTrue(
            self.client_app.allows_redirect_uri(self.redirect_uri),
        )
        self.assertFalse(
            self.client_app.allows_redirect_uri("https://evil.example/callback"),
        )
        self.assertTrue(
            self.client_app.allows_scope(MCP_SCOPE_READ),
        )
        self.assertTrue(
            self.client_app.allows_scopes(
                [
                    MCP_SCOPE_READ,
                    MCP_SCOPE_PROPOSALS_CREATE,
                ]
            ),
        )
        self.assertFalse(
            self.client_app.allows_scopes(
                [
                    MCP_SCOPE_READ,
                    "myscoope:admin",
                ]
            ),
        )

    def test_authorization_code_is_used_property(self):
        code = OAuthAuthorizationCode.objects.create(
            client=self.client_app,
            user=self.user,
            code_hash="abc123",
            redirect_uri=self.redirect_uri,
            scopes=[
                MCP_SCOPE_READ,
            ],
            code_challenge=self.code_challenge,
            code_challenge_method=OAUTH_CODE_CHALLENGE_METHOD_S256,
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        self.assertFalse(code.is_used)

        code.used_at = timezone.now()

        self.assertTrue(code.is_used)
