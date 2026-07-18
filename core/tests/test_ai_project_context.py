import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core.ai_project_context import build_ai_project_context


@override_settings(
    AI_ASSISTANT_OPENAI_API_KEY="ai-context-private-key",
    EMAIL_HOST_PASSWORD="ai-context-private-password",
)
class AiProjectContextTests(TestCase):
    def test_context_composes_existing_contracts_for_an_ai_client(self):
        payload = build_ai_project_context(include_database=False)

        self.assertEqual(payload["contract"], "myscoope.ai_project_context.v1")
        self.assertTrue(payload["client_posture"]["ai_is_current_client"])
        self.assertEqual(payload["source_contracts"]["project_status"], "myscoope.project_status.v1")
        self.assertTrue(payload["registry_health"]["valid"])
        self.assertTrue(any(cycle["id"] == "PCF00" for cycle in payload["live_cycles"]))
        self.assertTrue(payload["transitions"])
        self.assertTrue(payload["product_bets"])

    def test_context_excludes_secrets_and_private_user_rows(self):
        get_user_model().objects.create_user(
            username="context-private-user", email="context-private@example.com",
            password="private-password-value",
        )
        serialized = json.dumps(build_ai_project_context())

        for private_value in (
            "ai-context-private-key", "ai-context-private-password",
            "context-private@example.com", "private-password-value",
        ):
            self.assertNotIn(private_value, serialized)

    def test_domain_filter_returns_only_matching_decisions(self):
        payload = build_ai_project_context(
            domain="food_catalog", include_database=False, decision_limit=50
        )

        self.assertTrue(payload["decisions"])
        self.assertTrue(all(item["domain"] == "food_catalog" for item in payload["decisions"]))
        self.assertLessEqual(len(payload["decisions"]), 50)

