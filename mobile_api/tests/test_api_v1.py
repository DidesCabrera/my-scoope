from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.utils import timezone

from accounts.models import AccountDeletionRecord
from ai_assistant.models import AIAsyncJob, AIPreparedAction
from billing.application.contracts import AppleTransactionEvidence
from billing.models import AppleAppAccountToken, BillingProduct, PaymentProvider, ProviderSubscription
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
    WeightLog,
)


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIV1Tests(AuthenticatedMobileAPITestCase):
    def test_health_and_openapi_contract_are_public_and_versioned(self):
        health = Client().get("/api/v1/health")
        schema_response = Client().get("/api/v1/openapi.json")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json(), {"ok": True, "data": {"status": "ok", "api_version": "v1"}, "error": None})
        self.assertEqual(schema_response.status_code, 200)
        schema = schema_response.json()
        self.assertEqual(schema["info"]["version"], "1.0.0")
        for path in (
            "/api/v1/session",
            "/api/v1/me",
            "/api/v1/onboarding",
            "/api/v1/entitlements",
            "/api/v1/subscriptions",
            "/api/v1/subscriptions/apple/transactions",
            "/api/v1/program/active",
            "/api/v1/program/calendarizations",
            "/api/v1/program/calendarizations/history",
            "/api/v1/program/calendarizations/{calendarization_id}/pause",
            "/api/v1/program/calendarizations/{calendarization_id}/resume",
            "/api/v1/program/calendarizations/{calendarization_id}/cancel",
            "/api/v1/program/days/{day_id}",
            "/api/v1/proposals",
            "/api/v1/proposals/{proposal_id}",
            "/api/v1/proposals/{proposal_id}/approve",
            "/api/v1/proposals/{proposal_id}/reject",
            "/api/v1/proposals/{proposal_id}/cancel",
            "/api/v1/proposals/{proposal_id}/apply",
            "/api/v1/comparisons/metadata",
            "/api/v1/comparisons/options/{kind}",
            "/api/v1/comparisons/compare",
            "/api/v1/comparisons/saved",
            "/api/v1/comparisons/saved/{comparison_id}",
            "/api/v1/today",
            "/api/v1/days/{day_id}/meals/{meal_snapshot_key}/check-ins",
            "/api/v1/program/active/reminders",
            "/api/v1/notifications/apple/device",
            "/api/v1/program/reviews",
            "/api/v1/program/revisions",
            "/api/v1/program/revisions/{revision_id}/decision",
            "/api/v1/weights",
            "/api/v1/account/delete",
            "/api/v1/account/disclosures",
            "/api/v1/foods",
            "/api/v1/library/programs",
            "/api/v1/library/daily-plans",
            "/api/v1/library/meals",
            "/api/v1/library/foods",
            "/api/v1/library/meals/{meal_id}/food-picker/preview",
            "/api/v1/library/meals/{meal_id}/food-picker/commit",
            "/api/v1/library/daily-plans/{dailyplan_id}/meal-picker/preview",
            "/api/v1/library/daily-plans/{dailyplan_id}/meal-picker/commit",
            "/api/v1/library/programs/{program_id}/daily-plan-picker/preview",
            "/api/v1/library/programs/{program_id}/daily-plan-picker/commit",
            "/api/v1/library/programs/{program_id}/week-picker/preview",
            "/api/v1/library/programs/{program_id}/week-picker/commit",
            "/api/v1/library/meals/{meal_id}/foods/{meal_food_id}",
            "/api/v1/library/meals/{meal_id}/foods/order",
            "/api/v1/library/daily-plans/{dailyplan_id}/meals/{dailyplan_meal_id}",
            "/api/v1/library/daily-plans/{dailyplan_id}/meals/order",
            "/api/v1/library/programs/{program_id}/weeks/order",
            "/api/v1/library/programs/{program_id}/weeks/{week_number}/duplicate",
            "/api/v1/library/programs/{program_id}/weeks/{week_number}",
            "/api/v1/library/programs/{program_id}/weeks/{week_number}/days/{day_number}",
            "/api/v1/library/{entity}/{item_id}/actions",
            "/api/v1/foods/label-captures",
            "/api/v1/ai/turns",
            "/api/v1/ai/jobs/{job_id}",
            "/api/v1/ai/chats",
            "/api/v1/ai/chats/{chat_id}",
        ):
            self.assertIn(path, schema["paths"])
        for path in (
            "/api/v1/library/foods",
            "/api/v1/library/meals",
            "/api/v1/library/daily-plans",
            "/api/v1/library/programs",
        ):
            self.assertIn("post", schema["paths"][path])

    def test_protected_endpoint_uses_stable_error_envelope(self):
        response = Client().get("/api/v1/session")

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.json()["error"]["code"], "mobile_auth_required")

    def test_session_profile_and_entitlements_use_existing_authorities(self):
        session = self.client.get("/api/v1/session")
        profile = self.client.get("/api/v1/me")
        entitlements = self.client.get("/api/v1/entitlements")

        self.assertEqual(session.status_code, 200)
        self.assertEqual(session.json()["data"]["device_session_id"], str(self.device_session.public_id))
        self.assertEqual(profile.status_code, 200)
        self.assertFalse(profile.json()["data"]["onboarding_completed"])
        self.assertTrue(profile.json()["data"]["review_disclosure_required"])
        self.assertEqual(entitlements.status_code, 200)
        self.assertEqual(entitlements.json()["data"]["plan_slug"], "basic")

    def test_subscription_overview_is_consumer_only_and_uses_configured_apple_products(self):
        plan = self.user.account_subscription.plan
        product = BillingProduct.objects.create(
            provider=PaymentProvider.APPLE_APP_STORE,
            external_product_id="com.myscoope.basic.monthly",
            account_plan=plan,
            amount_minor=0,
        )

        with override_settings(BILLING_APPLE_PURCHASES_ENABLED=True):
            response = self.client.get("/api/v1/subscriptions")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertTrue(data["eligible"])
        self.assertTrue(data["purchases_enabled"])
        self.assertEqual(
            data["products"],
            [
                {
                    "product_id": product.external_product_id,
                    "plan_name": plan.name,
                    "interval": "month",
                }
            ],
        )
        self.assertNotIn("price", data["products"][0])
        self.assertTrue(AppleAppAccountToken.objects.filter(user=self.user).exists())

    @override_settings(BILLING_APPLE_PURCHASES_ENABLED=True)
    def test_apple_transaction_is_verified_server_side_before_projection(self):
        plan = self.user.account_subscription.plan
        product = BillingProduct.objects.create(
            provider=PaymentProvider.APPLE_APP_STORE,
            external_product_id="com.myscoope.basic.yearly",
            account_plan=plan,
            amount_minor=0,
            interval=BillingProduct.Interval.YEAR,
        )
        token = AppleAppAccountToken.objects.create(user=self.user)
        evidence = AppleTransactionEvidence(
            original_transaction_id="api-original",
            transaction_id="api-transaction",
            product_id=product.external_product_id,
            app_account_token=str(token.token),
            expires_date=int((timezone.now() + timedelta(days=365)).timestamp() * 1000),
            ownership_type="PURCHASED",
        )
        gateway = SimpleNamespace(verify_transaction=lambda value: evidence)

        with patch("mobile_api.api.build_apple_app_store_gateway", return_value=gateway):
            response = self.client.post(
                "/api/v1/subscriptions/apple/transactions",
                data={"signed_transaction": "header.payload.signature"},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ProviderSubscription.objects.filter(
                user=self.user,
                provider=PaymentProvider.APPLE_APP_STORE,
                status=ProviderSubscription.Status.AUTHORIZED,
            ).exists()
        )

    def test_onboarding_and_weight_endpoints_reuse_product_services(self):
        onboarding = self.client.post(
            "/api/v1/onboarding",
            data={
                "birth_date": "1990-05-10",
                "sex": "male",
                "height_cm": 188,
                "weight_kg": 84.5,
            },
            content_type="application/json",
        )
        weight = self.client.post(
            "/api/v1/weights",
            data={"weight_kg": 83.8, "measured_on": "2026-08-04"},
            content_type="application/json",
        )
        history = self.client.get("/api/v1/weights")

        self.assertEqual(onboarding.status_code, 200)
        self.assertTrue(onboarding.json()["data"]["onboarding_completed"])
        self.assertEqual(weight.status_code, 200)
        self.assertEqual(weight.json()["data"]["weight_kg"], 83.8)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["data"]["count"], 2)

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

    def test_account_deletion_is_available_through_the_mobile_contract(self):
        response = self.client.post(
            "/api/v1/account/delete",
            data={"confirmation": "ELIMINAR", "password": "mobile-pass-123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["receipt_id"])
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertEqual(AccountDeletionRecord.objects.count(), 1)
        self.assertFalse(WeightLog.objects.filter(user=self.user).exists())

    def test_mobile_disclosure_acceptance_is_versioned_and_persisted(self):
        response = self.client.post(
            "/api/v1/account/disclosures",
            data={"accepted": True},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["data"]["review_disclosure_required"])
        self.user.profile.refresh_from_db()
        self.assertEqual(
            self.user.profile.mobile_disclosure_version,
            self.user.profile.MOBILE_DISCLOSURE_VERSION,
        )
        self.assertIsNotNone(self.user.profile.mobile_disclosure_accepted_at)
