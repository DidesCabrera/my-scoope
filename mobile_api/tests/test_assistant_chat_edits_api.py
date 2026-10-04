from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.utils import timezone

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE
from notas.domain.models import AiNutritionChat


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIAssistantChatEditTests(AuthenticatedMobileAPITestCase):
    def test_ai_chat_rename_is_validated_owner_scoped_and_requires_write_scope(self):
        chat = AiNutritionChat.objects.create(
            user=self.user,
            title="Nombre original",
            conversation_payload={"messages": []},
        )

        renamed = self.client.patch(
            f"/api/v1/ai/chats/{chat.id}/name",
            data={"name": "  Plan semanal ajustado  "},
            content_type="application/json",
        )
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(renamed.json()["data"]["title"], "Plan semanal ajustado")
        chat.refresh_from_db()
        self.assertEqual(chat.title, "Plan semanal ajustado")

        blank = self.client.patch(
            f"/api/v1/ai/chats/{chat.id}/name",
            data={"name": "   "},
            content_type="application/json",
        )
        self.assertEqual(blank.status_code, 422)

        outsider = User.objects.create_user(username="ai-chat-rename-outsider")
        outsider_token = create_mcp_user_token(
            user=outsider,
            name="AI chat rename outsider token",
            scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE],
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        hidden = Client(HTTP_AUTHORIZATION=f"Bearer {outsider_token.raw_token}").patch(
            f"/api/v1/ai/chats/{chat.id}/name",
            data={"name": "Nombre ajeno"},
            content_type="application/json",
        )
        self.assertEqual(hidden.status_code, 404)

        read_only_token = create_mcp_user_token(
            user=self.user,
            name="AI chat rename read-only token",
            scopes=[MOBILE_SCOPE_READ],
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        forbidden = Client(HTTP_AUTHORIZATION=f"Bearer {read_only_token.raw_token}").patch(
            f"/api/v1/ai/chats/{chat.id}/name",
            data={"name": "Sin permiso"},
            content_type="application/json",
        )
        self.assertEqual(forbidden.status_code, 403)
