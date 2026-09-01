from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.utils import timezone

from ai_assistant.models import AIAsyncJob, AIPreparedAction
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.ai_tools.prepared_actions import prepare_product_action
from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_device_sessions import (
    MOBILE_SCOPE_READ,
    MOBILE_SCOPE_WRITE,
)
from notas.domain.models import (
    AiNutritionChat,
    Meal,
    SavedComparison,
)


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIAssistantTests(AuthenticatedMobileAPITestCase):
    @override_settings(AI_ASSISTANT_ASYNC_ENABLED=True)
    def test_ai_turn_uses_existing_durable_submit_and_poll_contract(self):
        submitted = self.client.post(
            "/api/v1/ai/turns",
            data={"message": "Ayúdame a ajustar mi plan", "idempotency_key": "mobile-turn-0001"},
            content_type="application/json",
        )

        self.assertEqual(submitted.status_code, 202)
        job_id = submitted.json()["data"]["job_id"]
        pending = self.client.get(f"/api/v1/ai/jobs/{job_id}")
        self.assertEqual(pending.status_code, 202)
        self.assertEqual(pending.json()["data"]["status"], AIAsyncJob.Status.QUEUED)

        chat = AiNutritionChat.objects.create(
            user=self.user,
            title="Ajuste móvil",
            conversation_payload={"messages": []},
        )
        AIAsyncJob.objects.filter(public_id=job_id).update(
            status=AIAsyncJob.Status.SUCCEEDED,
            result_payload={
                "contract": "myscoope.nutrition_intake_async_result.v1",
                "chat_id": chat.id,
                "conversation": {"messages": [{"role": "assistant", "text": "contenido privado"}]},
            },
        )
        completed = self.client.get(f"/api/v1/ai/jobs/{job_id}")
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json()["data"]["result"]["chat_id"], chat.id)
        self.assertTrue(completed.json()["data"]["result"]["conversation_updated"])
        self.assertNotIn("conversation", completed.json()["data"]["result"])

    @override_settings(AI_ASSISTANT_ASYNC_ENABLED=True)
    def test_ai_chat_history_is_typed_owner_scoped_and_reports_pending_turns(self):
        chat = AiNutritionChat.objects.create(
            user=self.user,
            title="Plan para entrenamiento",
            status=AiNutritionChat.STATUS_ACTIVE,
            last_message_preview="¿Cuántas comidas prefieres?",
            conversation_payload={
                "brief": {"raw_prompt": "Quiero rendir mejor"},
                "messages": [
                    {"role": "user", "text": "Quiero rendir mejor"},
                    {"role": "assistant", "text": "¿Cuántas comidas prefieres?"},
                    {"role": "system", "text": "no exponer"},
                ],
            },
        )
        pending_job = AIAsyncJob.objects.create(
            user=self.user,
            kind="nutrition_intake_turn",
            idempotency_key="pending-mobile-chat-0001",
            lane_key=f"nutrition-chat:{chat.id}",
            status=AIAsyncJob.Status.QUEUED,
            request_payload={"message": "Cuatro", "existing_chat_id": chat.id},
        )

        chat_list = self.client.get("/api/v1/ai/chats")
        detail = self.client.get(f"/api/v1/ai/chats/{chat.id}")

        self.assertEqual(chat_list.status_code, 200)
        self.assertEqual(chat_list.json()["data"]["items"][0]["id"], chat.id)
        self.assertTrue(chat_list.json()["data"]["availability"]["is_available"])
        self.assertEqual(detail.status_code, 200)
        self.assertEqual([message["role"] for message in detail.json()["data"]["messages"]], ["user", "assistant"])
        self.assertEqual(detail.json()["data"]["pending_turn"]["job_id"], str(pending_job.public_id))
        self.assertNotIn("brief", detail.json()["data"])
        self.assertNotIn("conversation_payload", detail.json()["data"])

        other_user = User.objects.create_user(username="ai-chat-outsider")
        other_token = create_mcp_user_token(
            user=other_user,
            name="AI chat outsider token",
            scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE],
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        outsider = Client(HTTP_AUTHORIZATION=f"Bearer {other_token.raw_token}")
        hidden = outsider.get(f"/api/v1/ai/chats/{chat.id}")
        self.assertEqual(hidden.status_code, 404)

        duplicate = self.client.post(
            "/api/v1/ai/turns",
            data={"message": "Otro mensaje", "idempotency_key": "pending-mobile-chat-0002", "chat_id": chat.id},
            content_type="application/json",
        )
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json()["error"]["code"], "assistant_turn_pending")
        self.assertEqual(AIAsyncJob.objects.filter(user=self.user, kind="nutrition_intake_turn").count(), 1)

    def test_ai_chat_projects_persisted_cards_and_ignores_unknown_payloads(self):
        meal = Meal.objects.create(name="Comida original", created_by=self.user, is_draft=False)
        action = prepare_product_action(
            user=self.user, action_key="meal.rename", target_id=meal.id, parameters={"name": "Comida confirmada"}
        )
        chat = AiNutritionChat.objects.create(
            user=self.user,
            title="Objetos persistidos",
            conversation_payload={
                "messages": [
                    {
                        "role": "assistant",
                        "text": "Revisa estos objetos.",
                        "profile_draft_card": {
                            "title": "Ficha",
                            "items": [{"key": "weight", "label": "Peso", "value": "80 kg"}],
                        },
                        "proposal_review_card": {
                            "proposal_id": 42,
                            "title": "Propuesta",
                            "summary": "Lista",
                            "status": "Pendiente",
                        },
                        "prepared_action_card": {
                            "id": str(action.public_id),
                            "title": "dato no confiable",
                            "summary": "dato no confiable",
                        },
                        "unknown_card": {"secret": "no exponer"},
                    }
                ]
            },
        )

        response = self.client.get(f"/api/v1/ai/chats/{chat.id}")

        self.assertEqual(response.status_code, 200)
        message = response.json()["data"]["messages"][0]
        self.assertEqual(
            [card["type"] for card in message["cards"]], ["profile_draft", "proposal_review", "prepared_action"]
        )
        self.assertEqual(message["cards"][2]["title"], action.title)
        self.assertNotIn("unknown_card", str(message))

    def test_ai_prepared_action_requires_owner_and_explicit_commit_or_cancel(self):
        meal = Meal.objects.create(name="Comida original", created_by=self.user, is_draft=False)
        action = prepare_product_action(
            user=self.user, action_key="meal.rename", target_id=meal.id, parameters={"name": "Comida confirmada"}
        )

        committed = self.client.post(f"/api/v1/ai/prepared-actions/{action.public_id}/commit")

        self.assertEqual(committed.status_code, 200)
        self.assertEqual(committed.json()["data"]["status"], AIPreparedAction.Status.COMMITTED)
        meal.refresh_from_db()
        self.assertEqual(meal.name, "Comida confirmada")
        repeated = self.client.post(f"/api/v1/ai/prepared-actions/{action.public_id}/commit")
        self.assertEqual(repeated.status_code, 409)
        self.assertEqual(repeated.json()["error"]["code"], "prepared_action_not_pending")

        destructive = prepare_product_action(user=self.user, action_key="meal.delete", target_id=meal.id)
        cancelled = self.client.post(f"/api/v1/ai/prepared-actions/{destructive.public_id}/cancel")
        self.assertEqual(cancelled.status_code, 200)
        self.assertTrue(Meal.objects.filter(id=meal.id).exists())

        other_user = User.objects.create_user(username="prepared-action-outsider")
        other_token = create_mcp_user_token(
            user=other_user,
            name="Outsider",
            scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE],
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        outsider = Client(HTTP_AUTHORIZATION=f"Bearer {other_token.raw_token}")
        hidden = outsider.post(f"/api/v1/ai/prepared-actions/{destructive.public_id}/commit")
        self.assertEqual(hidden.status_code, 404)

    @override_settings(AI_ASSISTANT_ASYNC_ENABLED=True)
    def test_ai_turn_accepts_only_an_owned_saved_comparison_as_typed_context(self):
        comparison = SavedComparison.objects.create(
            owner=self.user,
            kind=SavedComparison.KIND_FOODS,
            name="Desayunos",
            payload=[{"id": 1, "quantity": 100}, {"id": 2, "quantity": 100}],
            snapshot_payload=[{"id": 1, "name": "Avena"}, {"id": 2, "name": "Huevos"}],
        )

        accepted = self.client.post(
            "/api/v1/ai/turns",
            data={
                "message": "Ayúdame a elegir",
                "idempotency_key": "comparison-context-0001",
                "comparison_id": comparison.id,
            },
            content_type="application/json",
        )

        self.assertEqual(accepted.status_code, 202)
        job = AIAsyncJob.objects.get(public_id=accepted.json()["data"]["job_id"])
        context = job.request_payload["product_context"]
        self.assertEqual(context["saved_comparison_card"]["comparison_id"], comparison.id)
        self.assertEqual(context["saved_comparison"]["items"], ["Avena", "Huevos"])
        self.assertEqual(job.request_payload["message"], "Ayúdame a elegir")

        outsider = User.objects.create_user(username="comparison-context-outsider")
        foreign = SavedComparison.objects.create(owner=outsider, kind=SavedComparison.KIND_FOODS, name="Privada")
        denied = self.client.post(
            "/api/v1/ai/turns",
            data={
                "message": "Intenta abrirla",
                "idempotency_key": "comparison-context-0002",
                "comparison_id": foreign.id,
            },
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 422)
        self.assertEqual(denied.json()["error"]["code"], "saved_comparison_not_found")
