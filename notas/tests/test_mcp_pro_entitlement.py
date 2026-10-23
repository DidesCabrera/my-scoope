import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription
from notas.application.services.mcp_user_tokens import (
    MCP_SCOPE_READ,
    create_mcp_user_token,
    validate_mcp_user_token,
)
from notas.application.services.oauth_authorization_codes import (
    create_oauth_authorization_code,
    issue_oauth_access_token_from_authorization_code,
)
from notas.domain.models import OAuthClient


@override_settings(MCP_PRO_ENTITLEMENT_ENFORCED=True, MCP_RESOURCE_URL="https://mcp.example.test")
class MCPProEntitlementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mcp-pro-test")
        self.free = AccountPlan.objects.create(
            slug="free", name="Free", status=AccountPlan.Status.ACTIVE,
            entitlements={"integrations": {"mcp": {"enabled": False}}},
        )
        self.pro = AccountPlan.objects.create(
            slug="pro", name="Pro", status=AccountPlan.Status.ACTIVE,
            entitlements={"integrations": {"mcp": {"enabled": True}}},
        )
        self.subscription = AccountSubscription.objects.create(
            user=self.user, plan=self.free, status=AccountSubscription.Status.ACTIVE,
        )

    def _create_token(self):
        return create_mcp_user_token(
            user=self.user,
            name="MCP test",
            scopes=[MCP_SCOPE_READ],
            resource="https://mcp.example.test",
            expires_at=timezone.now() + timedelta(hours=1),
        )

    def test_only_active_pro_can_issue_and_use_mcp_token(self):
        with self.assertRaisesMessage(ValueError, "mcp_pro_required"):
            self._create_token()

        self.subscription.plan = self.pro
        self.subscription.save(update_fields=["plan"])
        created = self._create_token()
        self.assertTrue(validate_mcp_user_token(created.raw_token).ok)

        response = Client().post(
            reverse("ai_tools_list_user_proposals"),
            data=json.dumps({}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {created.raw_token}",
        )
        self.assertEqual(response.status_code, 200)

        self.subscription.plan = self.free
        self.subscription.save(update_fields=["plan"])
        denied = Client().post(
            reverse("ai_tools_list_user_proposals"),
            data=json.dumps({}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {created.raw_token}",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["error"]["code"], "mcp_pro_required")

    def test_expired_pro_period_denies_existing_token(self):
        self.subscription.plan = self.pro
        self.subscription.save(update_fields=["plan"])
        created = self._create_token()

        self.subscription.current_period_end = timezone.now() - timedelta(seconds=1)
        self.subscription.save(update_fields=["current_period_end"])
        self.assertEqual(
            validate_mcp_user_token(created.raw_token).error.code,
            "mcp_pro_required",
        )

    def test_mobile_scopes_are_not_commercially_gated(self):
        created = create_mcp_user_token(
            user=self.user, name="Mobile session", scopes=["mobile:read"],
        )
        self.assertTrue(validate_mcp_user_token(created.raw_token).ok)

    def test_oauth_exchange_rechecks_pro_after_authorization(self):
        self.subscription.plan = self.pro
        self.subscription.save(update_fields=["plan"])
        client = OAuthClient.objects.create(
            client_id="codex-mcp-test",
            client_name="Codex MCP test",
            redirect_uris=["http://127.0.0.1/callback"],
            allowed_scopes=[MCP_SCOPE_READ],
        )
        created = create_oauth_authorization_code(
            user=self.user,
            client=client,
            redirect_uri="http://127.0.0.1/callback",
            scopes=[MCP_SCOPE_READ],
            code_challenge="HbI_WMU4Dyn8dwHtH9MsCbSM-loQTudStz1c32xWk4s",
        )
        self.subscription.plan = self.free
        self.subscription.save(update_fields=["plan"])

        result = issue_oauth_access_token_from_authorization_code(
            raw_code=created.raw_code,
            client=client,
            redirect_uri="http://127.0.0.1/callback",
            code_verifier="test-code-verifier-123456789",
        )
        self.assertEqual(result.error.code, "mcp_pro_required")
