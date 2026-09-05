from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from accounts.seed_plans import seed_account_plans
from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_device_sessions import (
    MOBILE_SCOPE_ACCOUNT,
    MOBILE_SCOPE_READ,
    MOBILE_SCOPE_WRITE,
)
from notas.domain.models import OAuthClient, OAuthDeviceSession


class AuthenticatedMobileAPITestCase(TestCase):
    """Shared authenticated-device fixture for focused mobile API test modules."""

    def setUp(self) -> None:
        super().setUp()
        seed_account_plans()
        self.user = User.objects.create_user(
            username="mobile-api-user",
            email="mobile@example.com",
            password="mobile-pass-123",
            first_name="Felipe",
        )
        self.oauth_client = OAuthClient.objects.create(
            client_id="mobile-api-tests",
            client_name="Mobile API tests",
            redirect_uris=["myscoope://oauth/callback"],
            allowed_scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE, MOBILE_SCOPE_ACCOUNT],
        )
        self.device_session = OAuthDeviceSession.objects.create(
            client=self.oauth_client,
            user=self.user,
            device_id_hash="a" * 64,
            device_name="Test iPhone",
            platform=OAuthDeviceSession.PLATFORM_IOS,
        )
        created = create_mcp_user_token(
            user=self.user,
            name="Mobile API test token",
            scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE, MOBILE_SCOPE_ACCOUNT],
            expires_at=timezone.now() + timedelta(minutes=15),
            device_session=self.device_session,
        )
        self.raw_token = created.raw_token
        self.client = Client(HTTP_AUTHORIZATION=f"Bearer {self.raw_token}")
