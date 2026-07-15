import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone


class AIToolsAPIAdapterBaseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@example.com",
            password="pass123",
        )
        profile = self.user.profile
        profile.onboarding_completed_at = timezone.now()
        profile.onboarding_version = profile.ONBOARDING_VERSION_NUTRITION_V1
        profile.save(update_fields=["onboarding_completed_at", "onboarding_version"])

    def test_health_endpoint_requires_login(self):
        response = self.client.post(
            reverse("ai_tools_health"),
            data={},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 302)

    def test_health_endpoint_requires_post(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("ai_tools_health"),
        )

        self.assertEqual(response.status_code, 405)

        data = response.json()

        self.assertEqual(
            data,
            {
                "ok": False,
                "data": {},
                "error": {
                    "code": "method_not_allowed",
                    "message": "This endpoint only accepts POST requests.",
                    "details": {},
                },
            },
        )

    def test_health_endpoint_returns_ai_tool_result_shape(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("ai_tools_health"),
            data={},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(
            data,
            {
                "ok": True,
                "data": {
                    "status": "ok",
                    "adapter": "ai_tools_api",
                },
                "error": None,
            },
        )

        json.dumps(data)

    def test_health_endpoint_rejects_invalid_json(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("ai_tools_health"),
            data="{invalid json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()

        self.assertEqual(
            data,
            {
                "ok": False,
                "data": {},
                "error": {
                    "code": "invalid_json",
                    "message": "Request body must be valid JSON.",
                    "details": {},
                },
            },
        )

    def test_health_endpoint_rejects_non_object_json(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("ai_tools_health"),
            data=json.dumps(["not", "an", "object"]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()

        self.assertEqual(
            data["ok"],
            False,
        )
        self.assertEqual(
            data["error"]["code"],
            "json_body_must_be_object",
        )