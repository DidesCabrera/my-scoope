from django.test import Client, override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase


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
            "/api/v1/session", "/api/v1/me", "/api/v1/onboarding",
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
            "/api/v1/foods/label-captures", "/api/v1/foods/label-captures/config",
            "/api/v1/foods/label-captures/analyze",
            "/api/v1/foods/label-captures/{receipt_id}/image",
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
