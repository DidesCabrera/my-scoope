import base64
import hashlib

from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.services.mcp_user_tokens import validate_mcp_user_token
from notas.application.services.oauth_authorization_codes import create_oauth_authorization_code
from notas.application.services.oauth_device_sessions import (
    MOBILE_SCOPE_ACCOUNT,
    MOBILE_SCOPE_READ,
    MOBILE_SCOPE_WRITE,
    issue_mobile_tokens_from_authorization_code,
    revoke_oauth_device_session,
    rotate_mobile_refresh_token,
)
from notas.domain.models import OAuthClient, OAuthDeviceSession, OAuthRefreshToken


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


class OAuthDeviceSessionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mobile-user", password="pass123")
        self.client = OAuthClient.objects.get(client_id="myscoope-ios")
        self.redirect_uri = "myscoope://oauth/callback"
        self.verifier = "mobile-code-verifier-with-enough-entropy-123456789"
        self.device_id = "7a4626e1-1897-4f71-93dd-ae61ffd03fde"

    def _authorization_code(self):
        created = create_oauth_authorization_code(
            user=self.user,
            client=self.client,
            redirect_uri=self.redirect_uri,
            scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE, MOBILE_SCOPE_ACCOUNT],
            code_challenge=_pkce_challenge(self.verifier),
        )
        return created.raw_code

    def _issue(self):
        return issue_mobile_tokens_from_authorization_code(
            raw_code=self._authorization_code(),
            client=self.client,
            redirect_uri=self.redirect_uri,
            code_verifier=self.verifier,
            device_id=self.device_id,
            device_name="Felipe iPhone",
            platform=OAuthDeviceSession.PLATFORM_IOS,
        )

    def test_authorization_code_issues_device_bound_access_and_refresh_tokens(self):
        result = self._issue()

        self.assertTrue(result.ok)
        self.assertTrue(result.refresh_token.startswith("oauth_refresh_"))
        session = OAuthDeviceSession.objects.get(public_id=result.device_session_id)
        self.assertEqual(session.user, self.user)
        self.assertNotEqual(session.device_id_hash, self.device_id)
        self.assertEqual(session.refresh_tokens.count(), 1)

        validation = validate_mcp_user_token(result.access_token, required_scopes=[MOBILE_SCOPE_READ])
        self.assertTrue(validation.ok)
        self.assertEqual(validation.token.device_session, session)

    def test_refresh_rotation_rejects_reuse_and_revokes_the_device_session(self):
        first = self._issue()
        rotated = rotate_mobile_refresh_token(raw_refresh_token=first.refresh_token, client=self.client)

        self.assertTrue(rotated.ok)
        self.assertNotEqual(rotated.refresh_token, first.refresh_token)
        self.assertEqual(OAuthRefreshToken.objects.values("family_id").distinct().count(), 1)

        reused = rotate_mobile_refresh_token(raw_refresh_token=first.refresh_token, client=self.client)
        self.assertFalse(reused.ok)
        self.assertEqual(reused.error.code, "oauth_refresh_token_reused")

        session = OAuthDeviceSession.objects.get(public_id=first.device_session_id)
        self.assertFalse(session.is_active)
        validation = validate_mcp_user_token(rotated.access_token, required_scopes=[MOBILE_SCOPE_READ])
        self.assertFalse(validation.ok)
        self.assertEqual(validation.error.code, "mcp_user_token_revoked")

    def test_explicit_device_revocation_invalidates_access_and_refresh_tokens(self):
        issued = self._issue()

        self.assertTrue(revoke_oauth_device_session(user=self.user, public_id=issued.device_session_id))

        validation = validate_mcp_user_token(issued.access_token, required_scopes=[MOBILE_SCOPE_READ])
        self.assertFalse(validation.ok)
        self.assertEqual(validation.error.code, "mcp_user_token_revoked")
        refresh = OAuthRefreshToken.objects.get(session__public_id=issued.device_session_id)
        self.assertIsNotNone(refresh.revoked_at)

    def test_device_identifier_and_platform_are_validated(self):
        result = issue_mobile_tokens_from_authorization_code(
            raw_code=self._authorization_code(),
            client=self.client,
            redirect_uri=self.redirect_uri,
            code_verifier=self.verifier,
            device_id="short",
            device_name="Phone",
            platform="watchos",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "oauth_device_id_invalid")
