import json
from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from notas.domain.models import Meal, WeightLog
from notas.application.services.mcp_user_tokens import (
    MCP_SCOPE_PROPOSALS_CREATE,
    MCP_SCOPE_READ,
    create_mcp_user_token,
)


class AIToolsAPIMCPUserAuthTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@example.com",
            password="pass123",
        )

    def test_read_endpoint_accepts_mcp_user_token_with_read_scope(self):
        created = create_mcp_user_token(
            user=self.user,
            name="Read token",
            scopes=[
                MCP_SCOPE_READ,
            ],
        )

        response = self.client.post(
            reverse("ai_tools_list_user_proposals"),
            data=json.dumps({}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {created.raw_token}",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertTrue(data["ok"])
        self.assertIn(
            "proposals",
            data["data"],
        )
        self.assertIsNone(
            data["error"],
        )

    def test_meal_lookup_and_card_read_keep_user_token_scope(self):
        other = User.objects.create_user(username="other", password="pass123")
        WeightLog.objects.create(user=self.user, date=date.today(), weight_kg=80)
        own = Meal.objects.create(name="Mi almuerzo", created_by=self.user, is_public=False, is_draft=False)
        private = Meal.objects.create(name="Almuerzo privado", created_by=other, is_public=False, is_draft=False)
        token = create_mcp_user_token(
            user=self.user, name="Read token", scopes=[MCP_SCOPE_READ],
        ).raw_token

        def post(name, payload):
            return self.client.post(
                reverse(name), data=json.dumps(payload), content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            ).json()

        found = post("ai_tools_search_user_meals", {"query": "almuerzo"})
        self.assertTrue(found["ok"])
        self.assertEqual([row["id"] for row in found["data"]["meals"]], [own.id])
        visible = post("ai_tools_read_meal", {"meal_id": own.id})
        self.assertEqual(visible["data"]["meal"]["id"], own.id)
        denied = post("ai_tools_read_meal", {"meal_id": private.id})
        self.assertFalse(denied["ok"])
        self.assertNotIn("meal", denied["data"])

    def test_create_endpoint_rejects_mcp_user_token_without_create_scope(self):
        created = create_mcp_user_token(
            user=self.user,
            name="Read-only token",
            scopes=[
                MCP_SCOPE_READ,
            ],
        )

        response = self.client.post(
            reverse("ai_tools_create_validated_dailyplan_build_proposal"),
            data=json.dumps({}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {created.raw_token}",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        data = response.json()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "mcp_user_token_missing_scope",
        )

    def test_create_endpoint_accepts_mcp_user_token_with_create_scope(self):
        created = create_mcp_user_token(
            user=self.user,
            name="Create token",
            scopes=[
                MCP_SCOPE_PROPOSALS_CREATE,
            ],
        )

        response = self.client.post(
            reverse("ai_tools_create_validated_dailyplan_build_proposal"),
            data=json.dumps({}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {created.raw_token}",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        data = response.json()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "missing_required_field:dailyplan_id",
        )

    @override_settings(MCP_CREATE_MAX_PER_MINUTE=1, MCP_CREATE_MAX_PER_DAY=5)
    def test_mcp_create_is_rate_limited_per_token(self):
        created = create_mcp_user_token(
            user=self.user, name="Rate limited token", scopes=[MCP_SCOPE_PROPOSALS_CREATE],
        )
        requests = [
            self.client.post(
                reverse("ai_tools_create_validated_dailyplan_build_proposal"),
                data=json.dumps({}), content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {created.raw_token}",
            )
            for _ in range(2)
        ]
        self.assertEqual(requests[0].status_code, 400)
        self.assertEqual(requests[1].status_code, 429)
        self.assertEqual(requests[1].json()["error"]["code"], "mcp_create_rate_limited")
        self.assertEqual(requests[1]["Retry-After"], "60")

    @override_settings(MCP_MAX_REQUEST_BYTES=16)
    def test_mcp_request_body_size_is_bounded(self):
        created = create_mcp_user_token(
            user=self.user, name="Bounded token", scopes=[MCP_SCOPE_READ],
        )
        response = self.client.post(
            reverse("ai_tools_list_user_proposals"),
            data=json.dumps({"ignored": "x" * 30}), content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {created.raw_token}",
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "mcp_request_too_large")
