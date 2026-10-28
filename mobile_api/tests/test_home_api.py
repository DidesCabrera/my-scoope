from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from mobile_api.read_cache import home_cache_key, home_summary_cache_key
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import CalendarizedDay, DailyPlan, Food, Meal, Program, ProgramCalendarization, WeightLog


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileHomeAPITests(AuthenticatedMobileAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()

    def test_home_returns_the_complete_initial_projection(self) -> None:
        Food.objects.create(name="Avena", protein=13, carbs=68, fat=7, created_by=self.user)
        Meal.objects.create(name="Desayuno", created_by=self.user)
        DailyPlan.objects.create(name="Día base", created_by=self.user)
        Program.objects.create(name="Semana base", created_by=self.user)

        response = self.client.get("/api/v1/home")

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()["data"]
        self.assertEqual(
            data["library_counts"],
            {"food": 1, "meal": 1, "daily_plan": 1, "program": 1},
        )
        self.assertIn("today", data)
        self.assertIn("active_program", data)
        self.assertIn("pending_proposal_count", data)
        self.assertTrue(data["version"])

    def test_home_summary_skips_the_unused_active_program_projection(self) -> None:
        with patch("mobile_api.home.active_program_payload", side_effect=AssertionError("active program was loaded")):
            response = self.client.get("/api/v1/home/summary")

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()["data"]
        self.assertIn("today", data)
        self.assertIn("library_counts", data)
        self.assertNotIn("active_program", data)
        self.assertTrue(data["version"])

    def test_home_summary_is_smaller_and_uses_fewer_queries_with_an_active_program(self) -> None:
        today = timezone.localdate()
        program = Program.objects.create(name="Programa", created_by=self.user, duration_weeks=1)
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            source_program=program,
            program_name_snapshot=program.name,
            start_date=today,
            end_date=today + timedelta(days=6),
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        CalendarizedDay.objects.bulk_create([
            CalendarizedDay(
                user=self.user,
                calendarization=calendarization,
                calendar_date=today + timedelta(days=index),
                week_number=1,
                day_number=index + 1,
                plan_snapshot={"name": f"Plan {index}", "meals": []},
            )
            for index in range(7)
        ])

        with CaptureQueriesContext(connection) as summary_queries:
            summary = self.client.get("/api/v1/home/summary")
        with CaptureQueriesContext(connection) as complete_queries:
            complete = self.client.get("/api/v1/home")

        self.assertEqual(summary.status_code, 200, summary.content)
        self.assertEqual(complete.status_code, 200, complete.content)
        self.assertLess(len(summary_queries), len(complete_queries))
        self.assertLess(len(summary.content), len(complete.content))

    def test_home_supports_private_conditional_revalidation(self) -> None:
        first = self.client.get("/api/v1/home")
        etag = first.headers["ETag"]

        second = self.client.get("/api/v1/home", HTTP_IF_NONE_MATCH=etag)

        self.assertEqual(second.status_code, 304)
        self.assertEqual(second.headers["ETag"], etag)
        self.assertEqual(second.headers["Cache-Control"], "private, no-cache")
        self.assertIn("app;dur=", second.headers["Server-Timing"])
        self.assertRegex(second.headers["X-Request-ID"], r"^[A-Za-z0-9._:-]{1,128}$")

    def test_home_serializes_the_latest_weight_comment(self) -> None:
        weight = WeightLog.objects.create(
            user=self.user,
            date="2026-10-23",
            weight_kg=82.9,
            comment="Medición de prueba",
        )

        response = self.client.get("/api/v1/home")

        self.assertEqual(response.status_code, 200, response.content)
        latest_weight = response.json()["data"]["latest_weight"]
        self.assertEqual(latest_weight["id"], weight.id)
        self.assertEqual(latest_weight["measured_on"], "2026-10-23")
        self.assertIsNone(latest_weight["measured_time"])
        self.assertEqual(latest_weight["weight_kg"], 82.9)
        self.assertEqual(latest_weight["comment"], "Medición de prueba")
        self.assertEqual(latest_weight["source"], "manual")
        self.assertIsNotNone(latest_weight["created_at"])
        self.assertIsNone(latest_weight["calendarization_id"])

    def test_mobile_responses_preserve_render_request_correlation(self) -> None:
        response = self.client.get("/api/v1/home", HTTP_RNDR_ID="req-beta_123")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.headers["X-Request-ID"], "req-beta_123")

    def test_successful_mobile_write_invalidates_cached_home(self) -> None:
        self.client.get("/api/v1/home")
        self.client.get("/api/v1/home/summary")
        self.assertIsNotNone(cache.get(home_cache_key(self.user.id)))
        self.assertIsNotNone(cache.get(home_summary_cache_key(self.user.id)))

        response = self.client.post(
            "/api/v1/weights",
            data={"weight_kg": 81.2},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(cache.get(home_cache_key(self.user.id)))
        self.assertIsNone(cache.get(home_summary_cache_key(self.user.id)))

    def test_home_is_compressed_when_the_client_accepts_gzip(self) -> None:
        for index in range(12):
            Food.objects.create(
                name=f"Alimento de rendimiento {index}",
                protein=10,
                carbs=20,
                fat=5,
                created_by=self.user,
            )

        response = self.client.get("/api/v1/home", HTTP_ACCEPT_ENCODING="gzip")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.headers.get("Content-Encoding"), "gzip")
        self.assertIn("Accept-Encoding", response.headers.get("Vary", ""))

    def test_food_library_first_page_is_bounded_without_losing_the_total(self) -> None:
        Food.objects.bulk_create(
            [
                Food(name=f"Alimento {index}", protein=10, carbs=20, fat=5, created_by=self.user)
                for index in range(20)
            ]
        )

        response = self.client.get("/api/v1/library/foods?limit=12")

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()["data"]
        self.assertEqual(len(data["items"]), 12)
        self.assertEqual(data["total"], 20)
        self.assertLess(len(response.content), 100_000)
