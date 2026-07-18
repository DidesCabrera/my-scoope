import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from food_catalog.models import CatalogFood, CatalogImportBatch
from notas.domain.models import Food

from core.project_status import build_project_status


class ProjectStatusTests(TestCase):
    def test_report_combines_release_capabilities_migrations_and_safe_counts(self):
        CatalogFood.objects.create(
            display_name="Lenteja",
            canonical_name="Lenteja",
            protein_g_per_100g=9,
            carbs_g_per_100g=20,
            fat_g_per_100g=0.4,
            status=CatalogFood.STATUS_VERIFIED,
        )
        Food.objects.create(
            name="Lenteja operacional",
            protein=9,
            carbs=20,
            fat=0.4,
            is_global=True,
            is_active=True,
            is_verified=True,
        )

        report = build_project_status().as_dict()

        self.assertEqual(report["contract"], "myscoope.project_status.v1")
        migration_probe = next(item for item in report["probes"] if item["code"] == "database.migrations")
        catalog_probe = next(item for item in report["probes"] if item["code"] == "data.catalog")
        food_probe = next(item for item in report["probes"] if item["code"] == "data.operational_foods")
        self.assertTrue(migration_probe["data"]["up_to_date"])
        self.assertEqual(catalog_probe["data"]["foods_total"], 1)
        self.assertEqual(food_probe["data"]["global_active_verified"], 1)

    @override_settings(SENTRY_RELEASE="pcf-test-release")
    def test_json_command_uses_same_contract(self):
        output = StringIO()

        call_command("project_status", "--json", "--skip-database", stdout=output)
        payload = json.loads(output.getvalue())

        self.assertEqual(payload["release"]["commit"], "pcf-test-release")
        self.assertIn("ai_assistant", payload["capabilities"])
        self.assertEqual(
            [probe["code"] for probe in payload["probes"]],
            ["architecture.transitions", "product.portfolio"],
        )

    @override_settings(AI_ASSISTANT_OPENAI_API_KEY="private-key-value")
    def test_status_payload_contains_no_catalog_rows_or_private_user_data(self):
        get_user_model().objects.create_user(
            username="private-status-user",
            email="private-status@example.com",
            password="test-password",
        )
        CatalogImportBatch.objects.create(source_type="manual")
        payload = json.dumps(build_project_status().as_dict())

        self.assertNotIn("canonical_name", payload)
        self.assertNotIn("private-status@example.com", payload)
        self.assertNotIn("private-key-value", payload)
