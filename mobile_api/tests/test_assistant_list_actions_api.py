from django.contrib.auth.models import User
from django.test import override_settings

from ai_assistant.models import AIAsyncJob
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import AiNutritionChat


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIAssistantListActionTests(AuthenticatedMobileAPITestCase):
    def test_chat_list_can_be_bulk_deleted_with_owner_scope(self):
        older = AiNutritionChat.objects.create(user=self.user, title="Primero")
        newer = AiNutritionChat.objects.create(user=self.user, title="Segundo")

        listed = self.client.get("/api/v1/ai/chats")
        deleted = self.client.post(
            "/api/v1/ai/chats/bulk-delete",
            data={"item_ids": [older.id]},
            content_type="application/json",
        )

        self.assertEqual([item["id"] for item in listed.json()["data"]["items"]], [newer.id, older.id])
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(AiNutritionChat.objects.filter(id=older.id).exists())

        outsider = User.objects.create_user(username="chat-list-outsider")
        foreign = AiNutritionChat.objects.create(user=outsider, title="Privado")
        denied = self.client.post(
            "/api/v1/ai/chats/bulk-delete",
            data={"item_ids": [foreign.id]},
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertTrue(AiNutritionChat.objects.filter(id=foreign.id).exists())

    def test_chat_bulk_delete_skips_a_chat_with_a_pending_turn(self):
        chat = AiNutritionChat.objects.create(user=self.user, title="Procesando")
        AIAsyncJob.objects.create(
            user=self.user,
            kind="nutrition_intake_turn",
            idempotency_key="pending-delete-chat-0001",
            lane_key=f"nutrition-chat:{chat.id}",
            status=AIAsyncJob.Status.QUEUED,
        )

        response = self.client.post(
            "/api/v1/ai/chats/bulk-delete",
            data={"item_ids": [chat.id]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["skipped_ids"], [chat.id])
        self.assertTrue(AiNutritionChat.objects.filter(id=chat.id).exists())
