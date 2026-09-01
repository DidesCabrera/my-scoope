from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.utils import timezone

from accounts.models import AccountDeletionRecord
from ai_assistant.models import AIAsyncJob, AIPreparedAction
from billing.application.contracts import AppleTransactionEvidence
from billing.models import AppleAppAccountToken, BillingProduct, PaymentProvider, ProviderSubscription
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.ai_tools.prepared_actions import prepare_product_action
from notas.application.services.calendarization.snapshots import SNAPSHOT_SCHEMA_VERSION
from notas.application.services.commands.calendarization_execution_commands import prepare_calendarization_revision
from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_device_sessions import (
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
    FoodShare,
    Meal,
    MealFood,
    Program,
    ProgramCalendarization,
    ProgramDay,
    SavedComparison,
    WeightLog,
)


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPICalendarizationTests(AuthenticatedMobileAPITestCase):
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

    def test_today_and_active_program_resolve_from_current_calendarization(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        program = Program.objects.create(
            name="Definición 11 semanas",
            created_by=self.user,
            duration_weeks=11,
            is_draft=False,
        )
        dailyplan = DailyPlan.objects.create(name="Plan de hoy", created_by=self.user, is_draft=False)
        meal = Meal.objects.create(name="Comida de hoy", created_by=self.user, is_draft=False)
        slot = DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=meal)
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            source_program=program,
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
            plan_snapshot={
                "name": "Día alto en carbohidratos",
                "meals": [{"key": f"dailyplan_meal:{slot.id}", "name": meal.name}],
            },
        )

        today_response = self.client.get("/api/v1/today")
        active_response = self.client.get("/api/v1/program/active")

        self.assertEqual(today_response.status_code, 200)
        self.assertEqual(today_response.json()["data"]["day_id"], day.id)
        self.assertEqual(today_response.json()["data"]["plan_snapshot"]["name"], "Día alto en carbohidratos")
        self.assertEqual(today_response.json()["data"]["plan_snapshot"]["meals"][0]["detail_id"], meal.id)
        self.assertEqual(active_response.status_code, 200)
        self.assertEqual(active_response.json()["data"]["calendarization"]["id"], calendarization.id)
        self.assertEqual(active_response.json()["data"]["weeks_count"], 11)
        self.assertEqual(len(active_response.json()["data"]["weeks"]), 11)
        self.assertEqual(active_response.json()["data"]["weeks"][0]["week_number"], 1)
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
        hidden_calendarization = other_client.post(f"/api/v1/program/calendarizations/{calendarization_id}/pause")

        self.assertEqual(hidden_day.status_code, 404)
        self.assertEqual(hidden_calendarization.status_code, 404)

    def test_calendarized_day_exposes_owned_meal_detail_links_without_mutating_snapshot(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        dailyplan = DailyPlan.objects.create(name="Plan activo", created_by=self.user, is_draft=False)
        owned_meal = Meal.objects.create(name="Comida navegable", created_by=self.user, is_draft=False)
        owned_slot = DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=owned_meal)
        other = User.objects.create_user(username="calendar-meal-owner")
        foreign_meal = Meal.objects.create(name="Comida ajena", created_by=other, is_draft=False)
        foreign_slot = DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=foreign_meal)
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa activo",
            start_date=today,
            end_date=today,
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        stored_snapshot = {
            "name": "Plan activo",
            "totals": {"protein_g": 150, "carbs_g": 200, "fat_g": 60},
            "meals": [
                {"key": f"dailyplan_meal:{owned_slot.id}", "name": owned_meal.name, "totals": {"protein_g": 30}},
                {"key": f"dailyplan_meal:{foreign_slot.id}", "name": foreign_meal.name, "totals": {"protein_g": 15}},
            ],
        }
        day = CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=today,
            week_number=1,
            day_number=1,
            plan_snapshot=stored_snapshot,
        )

        response = self.client.get(f"/api/v1/program/days/{day.id}")

        self.assertEqual(response.status_code, 200)
        meals = response.json()["data"]["plan_snapshot"]["meals"]
        self.assertEqual(response.json()["data"]["plan_snapshot"]["totals"]["protein_per_kilogram"], 2.0)
        self.assertEqual(meals[0]["totals"]["protein_per_kilogram"], 0.4)
        self.assertEqual(meals[0]["detail_id"], owned_meal.id)
        self.assertNotIn("detail_id", meals[1])
        day.refresh_from_db()
        self.assertEqual(day.plan_snapshot, stored_snapshot)

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
        noted = self.client.post(
            f"/api/v1/days/{day.id}/meals/dailyplan_meal:99/check-ins",
            data={
                "action": "note",
                "idempotency_key": "mobile-checkin-note-0001",
                "note": "Cumplida según lo planificado.",
            },
            content_type="application/json",
        )
        reset = self.client.post(
            f"/api/v1/days/{day.id}/meals/dailyplan_meal:99/check-ins",
            data={"action": "reset", "idempotency_key": "mobile-checkin-0002"},
            content_type="application/json",
        )

        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json()["data"]["meal_execution"][0]["status"], "completed")
        self.assertEqual(noted.status_code, 200)
        self.assertEqual(noted.json()["data"]["meal_execution"][0]["status"], "completed")
        self.assertEqual(noted.json()["data"]["meal_execution"][0]["note"], "Cumplida según lo planificado.")
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.json()["data"]["meal_execution"][0]["status"], "planned")
        self.assertEqual(reset.json()["data"]["meal_execution"][0]["note"], "Cumplida según lo planificado.")
        day_detail = self.client.get(f"/api/v1/program/days/{day.id}")
        self.assertEqual(day_detail.status_code, 200)
        self.assertEqual(day_detail.json()["data"]["meal_execution"][0]["status"], "planned")
        self.assertEqual(day_detail.json()["data"]["meal_execution"][0]["note"], "Cumplida según lo planificado.")
        self.assertEqual(CalendarizedMealExecution.objects.filter(calendarized_day=day).count(), 3)

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
