from pathlib import Path

from django.test import TestCase

from notas.application.queries.food_catalog_queries import FoodCatalogItemDTO
from notas.domain.models import Food

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORT_SCRIPT = PROJECT_ROOT / "scripts" / "export_for_chatgpt.sh"
DECISION_PATH = PROJECT_ROOT / "docs" / "20_decisions" / "0018-food-catalog-cycle-closure.md"


class FoodCatalogCycleCompletionTests(TestCase):
    def test_operational_food_trace_fields_are_not_catalog_foreign_keys(self):
        catalog_trace_fields = (
            "catalog_food_id",
            "catalog_food_ref",
            "catalog_snapshot_version",
            "catalog_snapshot_payload",
            "catalog_snapshot_created_at",
            "catalog_sync_status",
        )

        for field_name in catalog_trace_fields:
            with self.subTest(field=field_name):
                field = Food._meta.get_field(field_name)
                self.assertIsNone(
                    field.remote_field,
                    msg=(
                        f"{field_name} must remain primitive snapshot trace metadata, "
                        "not a direct relation to food_catalog."
                    ),
                )

    def test_ai_food_catalog_dto_exposes_only_operational_food_id(self):
        field_names = set(FoodCatalogItemDTO.__dataclass_fields__)

        self.assertIn("food_id", field_names)
        self.assertNotIn("catalog_food_id", field_names)
        self.assertNotIn("catalog_food_ref", field_names)
        self.assertEqual(
            field_names,
            {
                "food_id",
                "name",
                "protein",
                "carbs",
                "fat",
                "kcal_per_100g",
                "unit",
                "source",
            },
        )

    def test_foodcatalog_export_includes_boundary_tests_for_next_cycles(self):
        script_text = EXPORT_SCRIPT.read_text()
        expected_includes = {
            "/food_catalog/tests/test_boundary_contracts.py",
            "/notas/tests/test_architecture_boundaries.py",
            "/notas/tests/test_domain_model_boundaries.py",
            "/notas/tests/test_food_catalog_cycle_completion.py",
            "/mcp_server/tests/test_mcp_protocol_boundaries.py",
            "/mcp_server/tests/test_mcp_food_catalog_tool.py",
        }

        for include_path in sorted(expected_includes):
            with self.subTest(include_path=include_path):
                self.assertIn(include_path, script_text)

    def test_cycle_closure_decision_records_final_boundary(self):
        decision_text = DECISION_PATH.read_text()

        self.assertIn("Ciclo Patch 32-40", decision_text)
        self.assertIn("notas.Food", decision_text)
        self.assertIn("MCP no accede a food_catalog", decision_text)
        self.assertIn("Patch 40", decision_text)
