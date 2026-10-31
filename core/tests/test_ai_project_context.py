import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from core.ai_project_context import build_ai_project_context, build_ai_task_packet


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
        self.assertTrue(
            all(cycle["status_class"] == "active" for cycle in payload["cycle_groups"]["active"])
        )
        self.assertTrue(
            any(
                cycle["id"] == "PCF00"
                for cycle in payload["cycle_groups"]["external_evidence_pending"]
            )
        )
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

    def test_compact_task_packet_exposes_the_smallest_workflow_boundary(self):
        payload = build_ai_task_packet(
            task_mode="consult",
            domain="food_catalog",
            surface="catalog import",
            include_database=False,
        )

        self.assertEqual(payload["contract"], "myscoope.ai_task_packet.v1")
        self.assertEqual(payload["task"]["mode"], "consult")
        self.assertEqual(payload["task"]["surface"], "catalog import")
        self.assertFalse(payload["workflow"]["fresh_checkout"])
        self.assertEqual(payload["workflow"]["destination"], "local")
        self.assertNotIn("project_status", payload)
        self.assertFalse(payload["product_bets"])
        self.assertTrue(
            all(item["owner"] == "food_catalog" for item in payload["transitions"])
        )
        self.assertTrue(
            all(item["domain"] == "food_catalog" for item in payload["decisions"])
        )
        for group in payload["cycles"].values():
            self.assertTrue(all(item["domain"] == "food_catalog" for item in group))

    def test_integration_packet_uses_changed_path_validation(self):
        payload = build_ai_task_packet(
            task_mode="integrate", include_database=False
        )

        self.assertEqual(payload["workflow"]["destination"], "staging")
        self.assertIn("changed-path tier", payload["workflow"]["validation"])

    def test_management_command_emits_compact_json_without_database_by_default(self):
        output = StringIO()

        call_command(
            "ai_project_context",
            compact=True,
            as_json=True,
            task_mode="consult",
            domain="food_catalog",
            stdout=output,
        )

        payload = json.loads(output.getvalue())
        self.assertEqual(payload["contract"], "myscoope.ai_task_packet.v1")
        self.assertEqual(payload["task"]["domain"], "food_catalog")

