from datetime import timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.models import AccountDeletionRecord
from accounts.seed_plans import seed_account_plans
from ai_assistant.models import AIAsyncJob
from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_device_sessions import (
    MOBILE_SCOPE_ACCOUNT,
    MOBILE_SCOPE_READ,
    MOBILE_SCOPE_WRITE,
)
from notas.domain.models import (
    CalendarizedDay,
    Food,
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
            "/api/v1/program/active",
            "/api/v1/today",
            "/api/v1/weights",
            "/api/v1/account/delete",
            "/api/v1/foods",
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
