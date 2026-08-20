from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.models import AccountDeletionRecord
from accounts.seed_plans import seed_account_plans
from ai_assistant.models import AIAsyncJob, AIPreparedAction
from billing.application.contracts import AppleTransactionEvidence
from billing.models import AppleAppAccountToken, BillingProduct, PaymentProvider, ProviderSubscription
from notas.application.ai_tools.prepared_actions import prepare_product_action
from notas.application.services.calendarization.snapshots import SNAPSHOT_SCHEMA_VERSION
from notas.application.services.commands.calendarization_execution_commands import prepare_calendarization_revision
from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_device_sessions import (
    MOBILE_SCOPE_ACCOUNT,
    MOBILE_SCOPE_READ,
    MOBILE_SCOPE_WRITE,
)
from notas.domain.models import (
    AiNutritionChat,
    ApplePushSubscription,
    CalendarizationMeasurementContext,
    CalendarizedDay,
    CalendarizedMealExecution,
    DailyPlan,
    DailyPlanMeal,
    Food,
    FoodLabelCaptureReceipt,
    Meal,
    MealFood,
    NutritionProposal,
    OAuthClient,
    OAuthDeviceSession,
    Program,
    ProgramCalendarization,
    ProgramDay,
    SavedComparison,
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
            "/api/v1/foods/label-captures",
            "/api/v1/ai/turns",
            "/api/v1/ai/jobs/{job_id}",
            "/api/v1/ai/chats",
            "/api/v1/ai/chats/{chat_id}",
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
        self.assertTrue(profile.json()["data"]["review_disclosure_required"])
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

    def test_calendarization_activation_requires_explicit_incomplete_and_replacement_confirmation(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        first_program = Program.objects.create(
            name="Programa incompleto",
            created_by=self.user,
            duration_weeks=1,
            is_draft=False,
        )
        first_payload = {
            "program_id": first_program.id,
            "start_date": today.isoformat(),
            "timezone_name": "UTC",
            "daily_notification_time": "07:00",
            "daily_notifications_enabled": True,
            "meal_notifications_enabled": False,
        }

        incomplete = self.client.post(
            "/api/v1/program/calendarizations",
            data=first_payload,
            content_type="application/json",
        )

        self.assertEqual(incomplete.status_code, 409)
        self.assertEqual(
            incomplete.json()["error"]["code"],
            "calendarization_incomplete_confirmation_required",
        )
        self.assertEqual(incomplete.json()["error"]["details"]["empty_count"], 7)

        first_payload["confirm_incomplete"] = True
        activated = self.client.post(
            "/api/v1/program/calendarizations",
            data=first_payload,
            content_type="application/json",
        )

        self.assertEqual(activated.status_code, 200)
        first_calendarization_id = activated.json()["data"]["calendarization"]["id"]
        self.assertEqual(len(activated.json()["data"]["empty_dates"]), 7)
        self.assertEqual(
            CalendarizedDay.objects.filter(calendarization_id=first_calendarization_id).count(),
            7,
        )

        second_program = Program.objects.create(
            name="Programa de reemplazo",
            created_by=self.user,
            duration_weeks=1,
            is_draft=False,
        )
        second_payload = {
            **first_payload,
            "program_id": second_program.id,
        }
        replacement_required = self.client.post(
            "/api/v1/program/calendarizations",
            data=second_payload,
            content_type="application/json",
        )

        self.assertEqual(replacement_required.status_code, 409)
        self.assertEqual(
            replacement_required.json()["error"]["code"],
            "calendarization_replacement_confirmation_required",
        )
        self.assertEqual(
            replacement_required.json()["error"]["details"]["current_calendarization_id"],
            first_calendarization_id,
        )

        second_payload["replace_current"] = True
        replaced = self.client.post(
            "/api/v1/program/calendarizations",
            data=second_payload,
            content_type="application/json",
        )

        self.assertEqual(replaced.status_code, 200)
        self.assertEqual(replaced.json()["data"]["replaced_calendarization_id"], first_calendarization_id)
        self.assertEqual(
            ProgramCalendarization.objects.get(pk=first_calendarization_id).status,
            ProgramCalendarization.STATUS_CANCELLED,
        )

    def test_calendarization_day_lifecycle_and_history_are_owned_by_the_mobile_user(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        program = Program.objects.create(
            name="Programa móvil",
            created_by=self.user,
            duration_weeks=1,
            is_draft=False,
        )
        activation = self.client.post(
            "/api/v1/program/calendarizations",
            data={
                "program_id": program.id,
                "start_date": today.isoformat(),
                "timezone_name": "UTC",
                "confirm_incomplete": True,
            },
            content_type="application/json",
        )
        calendarization_id = activation.json()["data"]["calendarization"]["id"]
        day_id = activation.json()["data"]["days"][0]["id"]

        day = self.client.get(f"/api/v1/program/days/{day_id}")
        paused = self.client.post(f"/api/v1/program/calendarizations/{calendarization_id}/pause")
        resumed = self.client.post(f"/api/v1/program/calendarizations/{calendarization_id}/resume")
        cancelled = self.client.post(f"/api/v1/program/calendarizations/{calendarization_id}/cancel")
        history = self.client.get("/api/v1/program/calendarizations/history")

        self.assertEqual(day.status_code, 200)
        self.assertFalse(day.json()["data"]["has_plan"])
        self.assertIsNone(day.json()["data"]["plan_snapshot"])
        self.assertEqual(paused.json()["data"]["calendarization"]["status"], "paused")
        self.assertEqual(resumed.json()["data"]["calendarization"]["status"], "active")
        self.assertIsNone(cancelled.json()["data"]["calendarization"])
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["data"]["count"], 1)
        self.assertEqual(history.json()["data"]["items"][0]["status"], "cancelled")

        other_user = User.objects.create_user(username="other-mobile-user")
        other_client = Client()
        other_token = create_mcp_user_token(
            user=other_user,
            name="Other mobile token",
            scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE],
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        other_client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {other_token.raw_token}"
        hidden_day = other_client.get(f"/api/v1/program/days/{day_id}")
        hidden_calendarization = other_client.post(
            f"/api/v1/program/calendarizations/{calendarization_id}/pause"
        )

        self.assertEqual(hidden_day.status_code, 404)
        self.assertEqual(hidden_calendarization.status_code, 404)

    def test_proposal_center_lists_details_and_separates_approval_from_application(self):
        food = Food.objects.create(
            name="Avena para propuesta",
            protein=13,
            carbs=68,
            fat=7,
            created_by=self.user,
        )
        context = DailyPlan.objects.create(
            name="Contexto de propuesta",
            created_by=self.user,
            is_draft=False,
        )
        proposal = NutritionProposal.objects.create(
            dailyplan=context,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            title="Desayuno propuesto",
            summary="Una comida revisable creada por AI.",
            targets={"protein": 30, "total_kcal": 500},
            current_snapshot={"dailyplan_id": context.id, "context": "meal_proposal"},
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Desayuno AI",
                    "foods": [{"food_id": food.id, "quantity": 100, "unit": "g"}],
                },
            },
            validation_summary={
                "payload_validation": {"is_valid": True, "intent": "create_meal"},
                "simulation": {
                    "intent": "create_meal",
                    "meal": {
                        "name": "Desayuno AI",
                        "foods": [{"food_id": food.id, "food_name": food.name, "quantity": 100, "unit": "g"}],
                        "kpis": {"protein": 13, "carbs": 68, "fat": 7, "total_kcal": 387},
                    },
                    "dailyplan": None,
                },
            },
        )

        proposal_list = self.client.get("/api/v1/proposals?status=pending_review")
        detail = self.client.get(f"/api/v1/proposals/{proposal.id}")
        approved = self.client.post(f"/api/v1/proposals/{proposal.id}/approve")

        self.assertEqual(proposal_list.status_code, 200)
        self.assertEqual(proposal_list.json()["data"]["pending_count"], 1)
        self.assertEqual(proposal_list.json()["data"]["items"][0]["id"], proposal.id)
        self.assertEqual({action["key"] for action in detail.json()["data"]["actions"]}, {"approve", "reject", "cancel"})
        self.assertEqual(detail.json()["data"]["meal"]["name"], "Desayuno AI")
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["data"]["status"], "approved")
        self.assertEqual(Meal.objects.filter(name="Desayuno AI").count(), 0)
        self.assertEqual([action["key"] for action in approved.json()["data"]["actions"]], ["apply", "cancel"])

        applied = self.client.post(
            f"/api/v1/proposals/{proposal.id}/apply",
            data={"acknowledge_external_subject": False},
            content_type="application/json",
        )
        replay = self.client.post(
            f"/api/v1/proposals/{proposal.id}/apply",
            data={"acknowledge_external_subject": False},
            content_type="application/json",
        )

        self.assertEqual(applied.status_code, 200)
        self.assertEqual(applied.json()["data"]["status"], "applied")
        self.assertEqual(applied.json()["data"]["applied_result"]["kind"], "meal")
        self.assertEqual(Meal.objects.filter(name="Desayuno AI").count(), 1)
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(Meal.objects.filter(name="Desayuno AI").count(), 1)

    def test_proposal_actions_require_ownership_and_external_subject_acknowledgement(self):
        food = Food.objects.create(name="Arroz AI", protein=3, carbs=28, fat=1, created_by=self.user)
        context = DailyPlan.objects.create(name="Contexto externo", created_by=self.user, is_draft=False)
        proposal = NutritionProposal.objects.create(
            dailyplan=context,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Comida para sujeto externo",
            targets={
                "subject_context": {
                    "source": "external_chat_data",
                    "requires_library_ppk_warning": True,
                    "calculation_weight_kg": 92,
                    "ppk_weight_source": "external_subject_weight",
                },
            },
            proposed_payload={
                "intent": "create_meal",
                "meal": {"name": "Comida externa", "foods": [{"food_id": food.id, "quantity": 100, "unit": "g"}]},
            },
        )

        warning = self.client.post(
            f"/api/v1/proposals/{proposal.id}/apply",
            data={"acknowledge_external_subject": False},
            content_type="application/json",
        )
        applied = self.client.post(
            f"/api/v1/proposals/{proposal.id}/apply",
            data={"acknowledge_external_subject": True},
            content_type="application/json",
        )

        other_user = User.objects.create_user(username="proposal-outsider")
        other_token = create_mcp_user_token(
            user=other_user,
            name="Proposal outsider token",
            scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE],
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        outsider = Client(HTTP_AUTHORIZATION=f"Bearer {other_token.raw_token}")
        hidden_detail = outsider.get(f"/api/v1/proposals/{proposal.id}")
        hidden_action = outsider.post(f"/api/v1/proposals/{proposal.id}/reject")

        self.assertEqual(warning.status_code, 409)
        self.assertEqual(warning.json()["error"]["code"], "proposal_external_subject_ack_required")
        self.assertEqual(applied.status_code, 200)
        self.assertEqual(applied.json()["data"]["status"], "applied")
        self.assertEqual(hidden_detail.status_code, 404)
        self.assertEqual(hidden_action.status_code, 404)

    def test_comparator_exposes_owned_options_and_authoritative_food_metrics(self):
        oats = Food.objects.create(
            name="Avena comparada",
            protein=10,
            carbs=20,
            fat=5,
            created_by=self.user,
        )
        rice = Food.objects.create(
            name="Arroz comparada",
            protein=3,
            carbs=28,
            fat=1,
            created_by=self.user,
        )
        other_user = User.objects.create_user(username="comparison-outsider")
        hidden = Food.objects.create(
            name="Alimento privado ajeno",
            protein=30,
            carbs=0,
            fat=2,
            created_by=other_user,
        )

        metadata = self.client.get("/api/v1/comparisons/metadata")
        options = self.client.get("/api/v1/comparisons/options/foods?search=comparada")
        compared = self.client.post(
            "/api/v1/comparisons/compare",
            data={
                "kind": "foods",
                "selections": [
                    {"id": oats.id, "quantity": 50},
                    {"id": rice.id, "quantity": 100},
                ],
            },
            content_type="application/json",
        )
        inaccessible = self.client.post(
            "/api/v1/comparisons/compare",
            data={
                "kind": "foods",
                "selections": [
                    {"id": oats.id, "quantity": 100},
                    {"id": hidden.id, "quantity": 100},
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(metadata.status_code, 200)
        self.assertEqual(
            [kind["key"] for kind in metadata.json()["data"]["kinds"]],
            ["foods", "meals", "dailyplans"],
        )
        self.assertNotIn("programs", [kind["key"] for kind in metadata.json()["data"]["kinds"]])
        self.assertEqual(options.status_code, 200)
        self.assertEqual({item["id"] for item in options.json()["data"]["items"]}, {oats.id, rice.id})
        self.assertEqual(compared.status_code, 200)
        first = compared.json()["data"]["items"][0]
        self.assertEqual(first["quantity"], 50.0)
        self.assertEqual(first["values"]["calories"], 82.5)
        self.assertEqual(first["values"]["protein_g"], 5.0)
        self.assertIsNone(first["values"]["protein_per_kilogram"])
        self.assertEqual(
            [metric["key"] for metric in compared.json()["data"]["metrics"]],
            ["total_kcal", "protein", "carbs", "fat", "alloc_protein", "alloc_carbs", "alloc_fat"],
        )
        calories = compared.json()["data"]["metrics"][0]
        self.assertEqual(calories["bars"][0]["formatted_value"], "82 kcal")
        self.assertEqual(calories["bars"][1]["relative_percentage"], 100.0)
        self.assertEqual(inaccessible.status_code, 404)
        self.assertEqual(inaccessible.json()["error"]["code"], "comparison_item_not_available")

        first_meal = Meal.objects.create(name="Comida uno", created_by=self.user, is_draft=False)
        second_meal = Meal.objects.create(name="Comida dos", created_by=self.user, is_draft=False)
        invalid_quantity = self.client.post(
            "/api/v1/comparisons/compare",
            data={
                "kind": "meals",
                "selections": [
                    {"id": first_meal.id, "quantity": 100},
                    {"id": second_meal.id},
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(invalid_quantity.status_code, 422)
        self.assertEqual(invalid_quantity.json()["error"]["code"], "comparison_quantity_not_allowed")

        repeated_food = self.client.post(
            "/api/v1/comparisons/compare",
            data={
                "kind": "foods",
                "selections": [{"id": oats.id}, {"id": oats.id, "quantity": 200}],
            },
            content_type="application/json",
        )
        self.assertEqual(repeated_food.status_code, 200)
        self.assertEqual([item["id"] for item in repeated_food.json()["data"]["items"]], [oats.id, oats.id])
        self.assertEqual([item["quantity"] for item in repeated_food.json()["data"]["items"]], [100.0, 200.0])
        self.assertEqual(
            [item["values"]["calories"] for item in repeated_food.json()["data"]["items"]],
            [165.0, 330.0],
        )
        self.assertEqual(
            [bar["relative_percentage"] for bar in repeated_food.json()["data"]["metrics"][0]["bars"]],
            [50.0, 100.0],
        )

    def test_saved_comparison_is_owner_scoped_and_preserves_its_snapshot(self):
        first_food = Food.objects.create(
            name="Avena original",
            protein=10,
            carbs=20,
            fat=5,
            created_by=self.user,
        )
        second_food = Food.objects.create(
            name="Arroz original",
            protein=3,
            carbs=28,
            fat=1,
            created_by=self.user,
        )
        request_payload = {
            "kind": "foods",
            "selections": [
                {"id": first_food.id, "quantity": 100},
                {"id": second_food.id, "quantity": 100},
            ],
        }
        saved = self.client.post(
            "/api/v1/comparisons/saved",
            data=request_payload,
            content_type="application/json",
        )
        self.assertEqual(saved.status_code, 200)
        comparison_id = saved.json()["data"]["saved_comparison_id"]

        first_food.name = "Avena modificada"
        first_food.protein = 20
        first_food.save(update_fields=["name", "protein"])

        historical = self.client.get(f"/api/v1/comparisons/saved/{comparison_id}")
        self.assertEqual(historical.status_code, 200)
        self.assertTrue(historical.json()["data"]["historical_snapshot"])
        self.assertEqual(historical.json()["data"]["items"][0]["name"], "Avena original")
        self.assertEqual(historical.json()["data"]["items"][0]["values"]["protein_g"], 10.0)

        refreshed = self.client.put(
            f"/api/v1/comparisons/saved/{comparison_id}",
            data=request_payload,
            content_type="application/json",
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(refreshed.json()["data"]["items"][0]["name"], "Avena modificada")
        self.assertEqual(refreshed.json()["data"]["items"][0]["values"]["protein_g"], 20.0)

        other_user = User.objects.create_user(username="saved-comparison-outsider")
        other_token = create_mcp_user_token(
            user=other_user,
            name="Saved comparison outsider token",
            scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE],
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        outsider = Client(HTTP_AUTHORIZATION=f"Bearer {other_token.raw_token}")
        hidden = outsider.get(f"/api/v1/comparisons/saved/{comparison_id}")
        self.assertEqual(hidden.status_code, 404)

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

    def test_personal_library_endpoints_match_the_four_web_library_entities(self):
        food = Food.objects.create(name="Avena personal", protein=13, carbs=68, fat=7, created_by=self.user)
        meal = Meal.objects.create(
            name="Desayuno reutilizable",
            created_by=self.user,
            is_draft=False,
            protein_cached=13,
            carbs_cached=68,
            fat_cached=7,
            total_kcal_cached=387,
            alloc_protein_cached=13.4,
            alloc_carbs_cached=70.3,
            alloc_fat_cached=16.3,
        )
        MealFood.objects.create(meal=meal, food=food, quantity=100)
        dailyplan = DailyPlan.objects.create(
            name="Día de entrenamiento",
            created_by=self.user,
            is_draft=False,
            summary_cache={"totals": {"protein": 13, "carbs": 68, "fat": 7, "total_kcal": 387, "alloc": {"protein": 13.4, "carbs": 70.3, "fat": 16.3}}},
        )
        embedded_meal = Meal.objects.create(
            name="Instancia del plan",
            created_by=self.user,
            is_draft=False,
            protein_cached=13,
            carbs_cached=68,
            fat_cached=7,
            kcal_protein_cached=52,
            kcal_carbs_cached=272,
            kcal_fat_cached=63,
            total_kcal_cached=387,
            alloc_protein_cached=13.4,
            alloc_carbs_cached=70.3,
            alloc_fat_cached=16.3,
        )
        MealFood.objects.create(meal=embedded_meal, food=food, quantity=100)
        DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=embedded_meal, hour="08:00")
        program = Program.objects.create(
            name="Programa base",
            created_by=self.user,
            duration_weeks=1,
            summary_cache={"filled_days_count": 1, "program_totals": {"protein": 13, "carbs": 68, "fat": 7, "kcal_protein": 52, "kcal_carbs": 272, "kcal_fat": 63}},
        )
        ProgramDay.objects.create(program=program, dailyplan=dailyplan, week_number=1, day_number=1)
        other = User.objects.create_user(username="private-library-owner")
        Food.objects.create(name="Alimento ajeno", protein=1, carbs=1, fat=1, created_by=other)

        expectations = {
            "/api/v1/library/foods": ("food", "Avena personal"),
            "/api/v1/library/meals": ("meal", "Desayuno reutilizable"),
            "/api/v1/library/daily-plans": ("dailyPlan", "Día de entrenamiento"),
            "/api/v1/library/programs": ("program", "Programa base"),
        }
        for path, (entity, name) in expectations.items():
            with self.subTest(path=path):
                response = self.client.get(path, {"search": name.split()[0]})
                self.assertEqual(response.status_code, 200)
                data = response.json()["data"]
                self.assertEqual(data["total"], 1)
                self.assertEqual(data["items"][0]["entity"], entity)
                self.assertEqual(data["items"][0]["name"], name)
                self.assertIn("nutrition", data["items"][0])
                self.assertIn("panel", data["items"][0])

        meal_item = self.client.get("/api/v1/library/meals").json()["data"]["items"][0]
        self.assertEqual(meal_item["panel"]["kind"], "foods")
        self.assertEqual(meal_item["panel"]["foods"][0]["name"], "Avena personal")
        self.assertEqual(meal_item["panel"]["foods"][0]["quantity"], 100.0)
        self.assertIn("calorie_share", meal_item["panel"]["foods"][0])
        self.assertIn("calorie_distribution", meal_item["panel"]["foods"][0])
        self.assertAlmostEqual(sum(meal_item["panel"]["foods"][0]["calorie_distribution"].values()), 100, places=1)

        dailyplan_item = self.client.get("/api/v1/library/daily-plans").json()["data"]["items"][0]
        self.assertEqual(dailyplan_item["panel"]["kind"], "meals")
        self.assertEqual(dailyplan_item["panel"]["meals"][0]["name"], "Instancia del plan")
        self.assertEqual(dailyplan_item["panel"]["meals"][0]["detail_id"], embedded_meal.id)
        self.assertEqual(dailyplan_item["panel"]["meals"][0]["foods"][0]["name"], "Avena personal")
        self.assertIn("calories", dailyplan_item["panel"]["meals"][0]["foods"][0])
        self.assertIn("calorie_distribution", dailyplan_item["panel"]["meals"][0]["foods"][0])
        self.assertIn("protein_allocation", dailyplan_item["panel"]["meals"][0]["foods"][0])
        self.assertIn("calorie_share", dailyplan_item["panel"]["meals"][0])
        self.assertIn("calorie_distribution", dailyplan_item["panel"]["meals"][0])

        program_item = self.client.get("/api/v1/library/programs").json()["data"]["items"][0]
        self.assertEqual(program_item["panel"]["kind"], "weeks")
        self.assertTrue(program_item["can_calendarize"])
        self.assertEqual(program_item["panel"]["weeks"][0]["days"][0]["plan_name"], "Día de entrenamiento")
        self.assertEqual(program_item["panel"]["weeks"][0]["filled_days_count"], 1)
        self.assertEqual(program_item["panel"]["weeks"][0]["days"][0]["nutrition"]["calories"], 387.0)
        self.assertEqual(program_item["panel"]["weeks"][0]["days"][0]["meals"][0]["name"], "Instancia del plan")
        self.assertEqual(program_item["panel"]["weeks"][0]["days"][0]["meals"][0]["foods"][0]["name"], "Avena personal")
        self.assertEqual(program_item["panel"]["weeks"][0]["foods"][0]["name"], "Avena personal")
        self.assertEqual(program_item["indicators"][1]["icon"], "dailyPlan")
        self.assertEqual(program_item["indicators"][2]["icon"], "food")
        self.assertIn("calorie_share", program_item["panel"]["weeks"][0])
        self.assertIn("calorie_distribution", program_item["panel"]["weeks"][0])

        detail_expectations = {
            f"/api/v1/library/foods/{food.id}": "food",
            f"/api/v1/library/meals/{meal.id}": "meal",
            f"/api/v1/library/daily-plans/{dailyplan.id}": "dailyPlan",
            f"/api/v1/library/programs/{program.id}": "program",
        }
        for path, entity in detail_expectations.items():
            with self.subTest(detail=path):
                detail = self.client.get(path)
                self.assertEqual(detail.status_code, 200)
                detail_data = detail.json()["data"]
                self.assertEqual(detail_data["entity"], entity)
                self.assertEqual(detail_data["creator"], self.user.get_full_name().strip() or self.user.username)
                if entity == "dailyPlan":
                    meal_data = detail_data["panel"]["meals"][0]
                    self.assertEqual(meal_data["foods"][0]["name"], "Avena personal")
                    self.assertIn("calories", meal_data["foods"][0])
                    self.assertIn("calorie_distribution", meal_data["foods"][0])
                if entity == "program":
                    week_data = detail_data["panel"]["weeks"][0]
                    self.assertEqual(week_data["filled_days_count"], 1)
                    self.assertEqual(week_data["average_calories"], 55.3)
                    self.assertEqual(week_data["days"][0]["dailyplan_id"], dailyplan.id)
                    self.assertEqual(week_data["days"][0]["nutrition"]["calories"], 387.0)
                    self.assertEqual(week_data["days"][0]["meals"][0]["name"], "Instancia del plan")
                    self.assertEqual(week_data["foods"][0]["name"], "Avena personal")

        embedded_meal_detail = self.client.get(f"/api/v1/library/meals/{embedded_meal.id}")
        self.assertEqual(embedded_meal_detail.status_code, 200)
        self.assertEqual(embedded_meal_detail.json()["data"]["name"], "Instancia del plan")

        missing = self.client.get("/api/v1/library/meals/999999")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["error"]["code"], "library_item_not_found")

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
        action = prepare_product_action(user=self.user, action_key="meal.rename", target_id=meal.id, parameters={"name": "Comida confirmada"})
        chat = AiNutritionChat.objects.create(
            user=self.user,
            title="Objetos persistidos",
            conversation_payload={"messages": [{
                "role": "assistant",
                "text": "Revisa estos objetos.",
                "profile_draft_card": {"title": "Ficha", "items": [{"key": "weight", "label": "Peso", "value": "80 kg"}]},
                "proposal_review_card": {"proposal_id": 42, "title": "Propuesta", "summary": "Lista", "status": "Pendiente"},
                "prepared_action_card": {"id": str(action.public_id), "title": "dato no confiable", "summary": "dato no confiable"},
                "unknown_card": {"secret": "no exponer"},
            }]},
        )

        response = self.client.get(f"/api/v1/ai/chats/{chat.id}")

        self.assertEqual(response.status_code, 200)
        message = response.json()["data"]["messages"][0]
        self.assertEqual([card["type"] for card in message["cards"]], ["profile_draft", "proposal_review", "prepared_action"])
        self.assertEqual(message["cards"][2]["title"], action.title)
        self.assertNotIn("unknown_card", str(message))

    def test_ai_prepared_action_requires_owner_and_explicit_commit_or_cancel(self):
        meal = Meal.objects.create(name="Comida original", created_by=self.user, is_draft=False)
        action = prepare_product_action(user=self.user, action_key="meal.rename", target_id=meal.id, parameters={"name": "Comida confirmada"})

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
        other_token = create_mcp_user_token(user=other_user, name="Outsider", scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE], expires_at=timezone.now() + timedelta(minutes=15))
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
            data={"message": "Ayúdame a elegir", "idempotency_key": "comparison-context-0001", "comparison_id": comparison.id},
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
            data={"message": "Intenta abrirla", "idempotency_key": "comparison-context-0002", "comparison_id": foreign.id},
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
