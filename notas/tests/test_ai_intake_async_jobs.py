from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from ai_assistant.application.chat_engines import ChatEngineTurnResult
from ai_assistant.models import AIAsyncJob
from notas.application.ai_intake.async_turns import (
    NUTRITION_INTAKE_TURN_RESULT_CONTRACT,
    process_nutrition_intake_turn_job,
)
from notas.application.ai_intake.chat_history import sync_chat_from_conversation
from notas.application.ai_intake.nutrition_brief import (
    build_conversation_from_brief,
    build_intake_result,
    serialize_conversation,
)


@override_settings(
    AI_ASSISTANT_ASYNC_ENABLED=True,
    CACHE_URL="",
    NUTRITION_ONBOARDING_GATE_ENABLED=False,
)
class AIIntakeAsyncJobViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="async-view-user")
        self.other = get_user_model().objects.create_user(username="other-async-user")
        self.client.force_login(self.user)

    def test_async_turn_submission_returns_202_and_is_idempotent(self):
        url = reverse("ai_nutrition_intake")
        payload = {
            "action": "analyze_prompt",
            "prompt": "Quiero mejorar mi alimentación",
            "is_async": "1",
        }

        first = self.client.post(
            url,
            payload,
            HTTP_ACCEPT="application/json",
            HTTP_IDEMPOTENCY_KEY="mobile-turn-1",
        )
        second = self.client.post(
            url,
            payload,
            HTTP_ACCEPT="application/json",
            HTTP_IDEMPOTENCY_KEY="mobile-turn-1",
        )

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(first.json()["job_id"], second.json()["job_id"])
        self.assertEqual(AIAsyncJob.objects.filter(user=self.user).count(), 1)

    def test_job_status_is_private_and_reports_pending(self):
        job = AIAsyncJob.objects.create(
            user=self.user,
            kind="nutrition_intake_turn",
            idempotency_key="pending",
            request_payload={},
        )

        response = self.client.get(reverse("ai_nutrition_async_job_status", args=[job.public_id]))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], AIAsyncJob.Status.QUEUED)

        self.client.force_login(self.other)
        response = self.client.get(reverse("ai_nutrition_async_job_status", args=[job.public_id]))
        self.assertEqual(response.status_code, 404)

    def test_successful_poll_restores_session_and_returns_thread(self):
        result = build_intake_result("Quiero mejorar mi alimentación")
        conversation = build_conversation_from_brief(brief=result.brief)
        chat = sync_chat_from_conversation(user=self.user, conversation=conversation)
        job = AIAsyncJob.objects.create(
            user=self.user,
            kind="nutrition_intake_turn",
            idempotency_key="success",
            request_payload={},
            status=AIAsyncJob.Status.SUCCEEDED,
            result_payload={
                "contract": NUTRITION_INTAKE_TURN_RESULT_CONTRACT,
                "conversation": serialize_conversation(conversation),
                "chat_id": chat.id,
                "prompt": result.prompt,
            },
        )

        response = self.client.get(reverse("ai_nutrition_async_job_status", args=[job.public_id]))

        self.assertEqual(response.status_code, 200)
        self.assertIn("thread_html", response.json())
        self.assertEqual(self.client.session["ai_nutrition_chat_id"], chat.id)

    def test_nutrition_handler_persists_chat_and_returns_serializable_contract(self):
        result = build_intake_result("Necesito un plan sencillo")
        conversation = build_conversation_from_brief(brief=result.brief)
        engine = Mock()
        engine.continue_chat.return_value = ChatEngineTurnResult(
            state=conversation,
            assistant_text="Cuéntame más",
        )
        job = AIAsyncJob.objects.create(
            user=self.user,
            kind="nutrition_intake_turn",
            idempotency_key="handler-success",
            request_payload={
                "message": "Necesito un plan sencillo",
                "existing_payload": {},
                "existing_chat_id": None,
            },
        )

        with patch(
            "notas.application.ai_intake.async_turns.get_nutrition_intake_chat_engine",
            return_value=engine,
        ):
            payload = process_nutrition_intake_turn_job(job=job)

        self.assertEqual(payload["contract"], NUTRITION_INTAKE_TURN_RESULT_CONTRACT)
        self.assertTrue(payload["chat_id"])
        request = engine.continue_chat.call_args.args[0]
        self.assertEqual(request.metadata["turn_id"], str(job.public_id))
        self.assertEqual(request.metadata["async_job_id"], str(job.public_id))
