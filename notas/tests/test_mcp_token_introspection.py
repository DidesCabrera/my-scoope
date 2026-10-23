from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription
from notas.application.services.mcp_user_tokens import (
    MCP_SCOPE_READ,
    create_mcp_user_token,
    revoke_mcp_user_token,
)


@override_settings(
    MCP_PRO_ENTITLEMENT_ENFORCED=True,
    MCP_RESOURCE_URL="https://mcp.example.test",
    NUTRITION_ONBOARDING_GATE_ENABLED=False,
)
class MCPTokenIntrospectionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="mcp-introspection-user")
        self.pro = AccountPlan.objects.create(
            slug="pro", name="Pro", status=AccountPlan.Status.ACTIVE,
            entitlements={"integrations": {"mcp": {"enabled": True}}},
        )
        self.free = AccountPlan.objects.create(
            slug="free", name="Free", status=AccountPlan.Status.ACTIVE,
            entitlements={"integrations": {"mcp": {"enabled": False}}},
        )
        self.subscription = AccountSubscription.objects.create(
            user=self.user, plan=self.pro, status=AccountSubscription.Status.ACTIVE,
        )

    def _token(self, **overrides):
        options = {
            "user": self.user,
            "name": "Codex connection",
            "scopes": [MCP_SCOPE_READ],
            "resource": "https://mcp.example.test",
            "expires_at": timezone.now() + timedelta(hours=1),
        }
        options.update(overrides)
        return create_mcp_user_token(**options)

    def _introspect(self, raw_token=""):
        return self.client.post(
            reverse("mcp_token_introspection"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}" if raw_token else "",
        )

    def test_valid_token_returns_only_actual_scopes_and_audience(self):
        created = self._token()
        with self.assertLogs("myscoope.mcp", level="INFO") as captured:
            response = self._introspect(created.raw_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        payload = response.json()
        self.assertEqual(payload["scopes"], [MCP_SCOPE_READ])
        self.assertEqual(payload["resource"], "https://mcp.example.test")
        self.assertGreater(payload["expires_at"], int(timezone.now().timestamp()))
        self.assertNotIn("user_id", payload)
        self.assertNotIn("token", payload)
        self.assertNotIn(created.raw_token, " ".join(captured.output))

    def test_fake_or_missing_token_cannot_introspect(self):
        self.assertEqual(self._introspect("mcp_user_invented").status_code, 401)
        self.assertEqual(self._introspect().status_code, 401)

    def test_revoked_and_expired_tokens_are_denied(self):
        revoked = self._token()
        revoke_mcp_user_token(revoked.token)
        self.assertEqual(self._introspect(revoked.raw_token).status_code, 401)
        expired = self._token()
        expired.token.expires_at = timezone.now() - timedelta(seconds=1)
        expired.token.save(update_fields=["expires_at"])
        self.assertEqual(self._introspect(expired.raw_token).status_code, 401)

    def test_wrong_audience_or_non_expiring_token_is_denied(self):
        wrong = self._token()
        wrong.token.resource = "https://other.example.test"
        wrong.token.save(update_fields=["resource"])
        self.assertEqual(self._introspect(wrong.raw_token).status_code, 401)
        non_expiring = self._token()
        non_expiring.token.expires_at = None
        non_expiring.token.save(update_fields=["expires_at"])
        self.assertEqual(self._introspect(non_expiring.raw_token).status_code, 401)

    def test_pro_downgrade_is_effective_immediately(self):
        created = self._token()
        self.subscription.plan = self.free
        self.subscription.save(update_fields=["plan"])
        self.assertEqual(self._introspect(created.raw_token).status_code, 401)

    def test_session_and_legacy_bearer_cannot_substitute_for_user_token(self):
        self.client.force_login(self.user)
        self.assertEqual(self._introspect().status_code, 401)
        self.assertEqual(self._introspect("technical-secret").status_code, 401)

    @override_settings(MCP_AUTH_MAX_PER_IP_PER_MINUTE=1)
    def test_auth_attempts_are_rate_limited_by_source_address(self):
        url = reverse("mcp_token_introspection")
        first = self.client.post(
            url, HTTP_AUTHORIZATION="Bearer mcp_user_invented", REMOTE_ADDR="203.0.113.245",
        )
        second = self.client.post(
            url, HTTP_AUTHORIZATION="Bearer mcp_user_invented", REMOTE_ADDR="203.0.113.245",
        )
        self.assertEqual(first.status_code, 401)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second["Retry-After"], "60")
