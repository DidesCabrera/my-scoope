from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.utils import timezone

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_READ


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIIdentityEditTests(AuthenticatedMobileAPITestCase):
    def test_username_rename_updates_session_and_persists(self):
        response = self.client.patch(
            "/api/v1/account/username",
            data={"username": "  felipe.nutricion  "},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["username"], "felipe.nutricion")
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "felipe.nutricion")

    def test_username_rename_rejects_blank_invalid_and_unavailable_values(self):
        User.objects.create_user(username="NombreOcupado")

        for username, code in (
            ("   ", "account_username_required"),
            ("nombre con espacios", "account_username_invalid"),
            ("nombreocupado", "account_username_unavailable"),
        ):
            with self.subTest(username=username):
                response = self.client.patch(
                    "/api/v1/account/username",
                    data={"username": username},
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["error"]["code"], code)

    def test_username_rename_requires_account_scope(self):
        read_only_token = create_mcp_user_token(
            user=self.user,
            name="Username rename read-only token",
            scopes=[MOBILE_SCOPE_READ],
            expires_at=timezone.now() + timedelta(minutes=15),
        )

        response = Client(HTTP_AUTHORIZATION=f"Bearer {read_only_token.raw_token}").patch(
            "/api/v1/account/username",
            data={"username": "sin-permiso"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
