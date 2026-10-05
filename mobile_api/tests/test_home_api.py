from __future__ import annotations

from django.core.cache import cache
from django.test import override_settings

from mobile_api.read_cache import home_cache_key
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import DailyPlan, Food, Meal, Program


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

    def test_home_supports_private_conditional_revalidation(self) -> None:
        first = self.client.get("/api/v1/home")
        etag = first.headers["ETag"]

        second = self.client.get("/api/v1/home", HTTP_IF_NONE_MATCH=etag)

        self.assertEqual(second.status_code, 304)
        self.assertEqual(second.headers["ETag"], etag)
        self.assertEqual(second.headers["Cache-Control"], "private, no-cache")
        self.assertIn("app;dur=", second.headers["Server-Timing"])

    def test_successful_mobile_write_invalidates_cached_home(self) -> None:
        self.client.get("/api/v1/home")
        self.assertIsNotNone(cache.get(home_cache_key(self.user.id)))

        response = self.client.post(
            "/api/v1/weights",
            data={"weight_kg": 81.2},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(cache.get(home_cache_key(self.user.id)))

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
