from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.models import AccountDeletionRecord
from accounts.seed_plans import seed_account_plans
from ai_assistant.models import AIAsyncJob
from billing.application.contracts import AppleTransactionEvidence
from billing.models import AppleAppAccountToken, BillingProduct, PaymentProvider, ProviderSubscription
from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_device_sessions import (
    MOBILE_SCOPE_ACCOUNT,
    MOBILE_SCOPE_READ,
    MOBILE_SCOPE_WRITE,
)
from notas.application.services.calendarization.snapshots import SNAPSHOT_SCHEMA_VERSION
from notas.application.services.commands.calendarization_execution_commands import prepare_calendarization_revision
from notas.domain.models import (
    ApplePushSubscription,
    CalendarizedDay,
    CalendarizedMealExecution,
    CalendarizationMeasurementContext,
    Food,
    FoodLabelCaptureReceipt,
    OAuthClient,
    OAuthDeviceSession,
    ProgramCalendarization,
    WeightLog,
)


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIV1Tests(TestCase):
    def setUp(self):
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
            "/api/v1/today",
            "/api/v1/days/{day_id}/meals/{meal_snapshot_key}/check-ins",
            "/api/v1/program/active/reminders",
            "/api/v1/notifications/apple/device",
            "/api/v1/program/reviews",
            "/api/v1/program/revisions",
            "/api/v1/program/revisions/{revision_id}/decision",
            "/api/v1/weights",
            "/api/v1/account/delete",
            "/api/v1/foods",
            "/api/v1/foods/label-captures",
            "/api/v1/ai/turns",
            "/api/v1/ai/jobs/{job_id}",
        ):
            self.assertIn(path, schema["paths"])

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
        self.assertEqual(entitlements.status_code, 200)
        self.assertEqual(entitlements.json()["data"]["plan_slug"], "basic")

    def test_apple_notification_device_is_bound_to_authenticated_device_session(self):
        response = self.client.put(
            "/api/v1/notifications/apple/device",
            data={"device_token": "ab" * 32, "environment": "sandbox"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["delivery_mode"], "local")
        subscription = ApplePushSubscription.objects.get(device_session=self.device_session)
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.environment, ApplePushSubscription.ENVIRONMENT_SANDBOX)
        self.assertNotEqual(subscription.token_fingerprint, subscription.device_token)

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
        self.assertEqual(data["products"], [{
            "product_id": product.external_product_id,
            "plan_name": plan.name,
            "interval": "month",
        }])
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

    def test_today_and_active_program_resolve_from_current_calendarization(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Definición 8 semanas",
            start_date=today,
            end_date=today + timedelta(days=6),
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        day = CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=today,
            week_number=1,
            day_number=1,
            plan_snapshot={"name": "Día alto en carbohidratos", "meals": []},
        )

        today_response = self.client.get("/api/v1/today")
        active_response = self.client.get("/api/v1/program/active")

        self.assertEqual(today_response.status_code, 200)
        self.assertEqual(today_response.json()["data"]["day_id"], day.id)
        self.assertEqual(today_response.json()["data"]["plan_snapshot"]["name"], "Día alto en carbohidratos")
        self.assertEqual(active_response.status_code, 200)
        self.assertEqual(active_response.json()["data"]["calendarization"]["id"], calendarization.id)
        self.assertEqual(len(active_response.json()["data"]["days"]), 1)

    def test_today_check_in_persists_append_only_execution_evidence(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa en ejecución",
            start_date=today,
            end_date=today + timedelta(days=6),
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        day = CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=today,
            week_number=1,
            day_number=1,
            plan_snapshot={
                "schema_version": SNAPSHOT_SCHEMA_VERSION,
                "name": "Día ejecutable",
                "meals": [{"key": "dailyplan_meal:99", "name": "Desayuno", "hour": "08:00", "foods": []}],
                "totals": {},
            },
        )

        completed = self.client.post(
            f"/api/v1/days/{day.id}/meals/dailyplan_meal:99/check-ins",
            data={"action": "completed", "idempotency_key": "mobile-checkin-0001"},
            content_type="application/json",
        )
        reset = self.client.post(
            f"/api/v1/days/{day.id}/meals/dailyplan_meal:99/check-ins",
            data={"action": "reset", "idempotency_key": "mobile-checkin-0002"},
            content_type="application/json",
        )

        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json()["data"]["meal_execution"][0]["status"], "completed")
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.json()["data"]["meal_execution"][0]["status"], "planned")
        self.assertEqual(CalendarizedMealExecution.objects.filter(calendarized_day=day).count(), 2)

    def test_reviews_reminders_and_measurement_context_share_the_active_program(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa medible",
            start_date=today,
            end_date=today + timedelta(days=6),
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=today,
            week_number=1,
            day_number=1,
            plan_snapshot={
                "schema_version": SNAPSHOT_SCHEMA_VERSION,
                "name": "Día uno",
                "meals": [{"key": "dailyplan_meal:1", "name": "Comida", "hour": "20:00", "foods": []}],
                "totals": {},
            },
        )

        weight = self.client.post(
            "/api/v1/weights",
            data={"weight_kg": 81.2, "measured_on": today.isoformat()},
            content_type="application/json",
        )
        review = self.client.post(
            "/api/v1/program/reviews",
            data={
                "period_start": today.isoformat(),
                "period_end": today.isoformat(),
                "idempotency_key": "mobile-review-0001",
                "energy_score": 4,
                "hunger_score": 2,
                "training_performance_score": 5,
                "note": "Buen rendimiento.",
            },
            content_type="application/json",
        )
        reminders = self.client.put(
            "/api/v1/program/active/reminders",
            data={
                "timezone_name": "America/Santiago",
                "daily_notification_time": "07:30",
                "daily_notifications_enabled": True,
                "meal_notifications_enabled": True,
            },
            content_type="application/json",
        )

        self.assertEqual(weight.status_code, 200)
        self.assertEqual(weight.json()["data"]["calendarization_id"], calendarization.id)
        self.assertEqual(CalendarizationMeasurementContext.objects.filter(calendarization=calendarization).count(), 1)
        self.assertEqual(reminders.status_code, 200)
        self.assertTrue(reminders.json()["data"]["meal_notifications_enabled"])
        self.assertEqual(reminders.json()["data"]["timezone_name"], "America/Santiago")
        self.assertEqual(review.status_code, 200)
        self.assertEqual(review.json()["data"]["summary_snapshot"]["measurements"]["latest_weight_kg"], 81.2)

    def test_mobile_can_decide_but_cannot_inject_a_prospective_revision(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa revisable",
            start_date=today,
            end_date=today + timedelta(days=6),
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        future_day = CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=today + timedelta(days=1),
            week_number=1,
            day_number=2,
            plan_snapshot={
                "schema_version": SNAPSHOT_SCHEMA_VERSION,
                "name": "Plan original",
                "meals": [],
                "totals": {"total_kcal": 2200},
            },
        )
        revision = prepare_calendarization_revision(
            user=self.user,
            calendarization_id=calendarization.id,
            effective_from=future_day.calendar_date,
            replacement_days=[
                {
                    "calendar_date": future_day.calendar_date,
                    "plan_snapshot": {
                        "schema_version": SNAPSHOT_SCHEMA_VERSION,
                        "name": "Plan revisado",
                        "meals": [],
                        "totals": {"total_kcal": 2050},
                    },
                }
            ],
            rationale="Cambio futuro preparado por una autoridad interna.",
            idempotency_key="mobile-revision-0001",
        )

        listed = self.client.get("/api/v1/program/revisions")
        decided = self.client.post(
            f"/api/v1/program/revisions/{revision.id}/decision",
            data={"decision": "approve"},
            content_type="application/json",
        )

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["items"][0]["days"][0]["after_name"], "Plan revisado")
        self.assertEqual(decided.status_code, 200)
        self.assertEqual(decided.json()["data"]["status"], "applied")
        future_day.refresh_from_db()
        self.assertEqual(future_day.plan_snapshot["name"], "Plan revisado")
        self.assertEqual(
            self.client.post("/api/v1/program/revisions", data={}, content_type="application/json").status_code,
            405,
        )

    def test_write_scope_is_required_for_mutations(self):
        read_only = create_mcp_user_token(
            user=self.user,
            name="Read-only mobile token",
            scopes=[MOBILE_SCOPE_READ],
            expires_at=timezone.now() + timedelta(minutes=15),
            device_session=self.device_session,
        )
        client = Client(HTTP_AUTHORIZATION=f"Bearer {read_only.raw_token}")

        response = client.post(
            "/api/v1/weights",
            data={"weight_kg": 83.8},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "mobile_scope_missing")

    def test_food_search_is_paginated_and_respects_existing_visibility(self):
        Food.objects.create(name="Arroz personal", protein=7, carbs=78, fat=1, created_by=self.user)
        Food.objects.create(name="Arroz global", protein=8, carbs=77, fat=1, created_by=None, is_global=True)
        other = User.objects.create_user(username="other-user")
        Food.objects.create(name="Arroz privado ajeno", protein=9, carbs=70, fat=2, created_by=other)

        response = self.client.get("/api/v1/foods", {"search": "Arroz", "offset": 0, "limit": 1})

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["limit"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertTrue(data["items"][0]["is_user_food"])

    def test_confirmed_label_capture_creates_only_a_private_food_and_is_idempotent(self):
        payload = {
            "name": "Yogur alto en proteína",
            "protein_g": 10.2,
            "carbs_g": 4.1,
            "fat_g": 0.4,
            "saturated_fat_g": 0.2,
            "sugar_g": 3.7,
            "fiber_g": 0,
            "sodium_mg": 48,
            "serving_size_g": 150,
            "declared_energy_kcal_per_100g": 61,
            "detected_basis": "per_serving",
            "ocr_engine": "apple_vision",
            "ocr_engine_version": "1",
            "field_confidence": {"protein_g": 0.94, "carbs_g": 0.89},
            "warnings": ["energy_macro_mismatch"],
            "idempotency_key": "label-capture-0001",
        }

        first = self.client.post("/api/v1/foods/label-captures", data=payload, content_type="application/json")
        second = self.client.post("/api/v1/foods/label-captures", data=payload, content_type="application/json")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["data"]["id"], second.json()["data"]["id"])
        food = Food.objects.get(pk=first.json()["data"]["id"])
        self.assertEqual(food.created_by, self.user)
        self.assertFalse(food.is_global)
        self.assertFalse(food.is_verified)
        self.assertFalse(food.solver_enabled)
        self.assertEqual(FoodLabelCaptureReceipt.objects.count(), 1)
        receipt = food.label_capture_receipt
        self.assertEqual(receipt.ocr_engine, "apple_vision")
        self.assertNotIn("raw_text", receipt.field_confidence)

    def test_label_capture_rejects_an_idempotency_key_reused_for_different_values(self):
        payload = {
            "name": "Producto privado",
            "protein_g": 10,
            "carbs_g": 20,
            "fat_g": 5,
            "detected_basis": "per_100g",
            "ocr_engine": "apple_vision",
            "field_confidence": {},
            "warnings": [],
            "idempotency_key": "label-capture-0002",
        }
        self.client.post("/api/v1/foods/label-captures", data=payload, content_type="application/json")
        payload["protein_g"] = 11

        conflict = self.client.post("/api/v1/foods/label-captures", data=payload, content_type="application/json")

        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["error"]["code"], "food_label_idempotency_conflict")

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

        AIAsyncJob.objects.filter(public_id=job_id).update(
            status=AIAsyncJob.Status.SUCCEEDED,
            result_payload={"contract": "test.mobile.ai.v1", "conversation": {"messages": []}},
        )
        completed = self.client.get(f"/api/v1/ai/jobs/{job_id}")
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json()["data"]["result"]["contract"], "test.mobile.ai.v1")

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
