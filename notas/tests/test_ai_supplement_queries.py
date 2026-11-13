from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from ai_assistant.application.objective_state import infer_active_work
from ai_assistant.application.tools.registry import get_tool_spec
from notas.application.ai_tools.workspace_query_tools import query_workspace_tool
from notas.domain.models import (
    DailyPlan,
    Supplement,
    SupplementIntake,
    SupplementIntakeItem,
    SupplementIntakePreset,
    SupplementIntakePresetItem,
)


class AISupplementQueryTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="supp-ai-owner")
        self.other = user_model.objects.create_user(username="supp-ai-other")
        self.owned = Supplement.objects.create(
            created_by=self.owner,
            name="Vitamina de prueba",
            brand="Marca de prueba",
            nutrition={"energy_kcal": "12"},
            user_information="información personal que no debe ir al proveedor",
        )
        self.foreign = Supplement.objects.create(created_by=self.other, name="Suplemento ajeno")

    def test_query_is_owner_scoped_and_never_adds_label_nutrition_to_totals(self):
        with patch("notas.application.ai_tools.supplement_read_tools.require_supplements_pro"):
            listed = query_workspace_tool(self.owner, resource="supplements")
            detail = query_workspace_tool(self.owner, resource="supplements", object_id=self.owned.id)
            foreign = query_workspace_tool(self.owner, resource="supplements", object_id=self.foreign.id)

        self.assertTrue(listed.ok)
        self.assertEqual(listed.data["total_count"], 1)
        self.assertEqual(listed.data["items"][0]["name"], "Vitamina de prueba")
        self.assertEqual(detail.data["nutrition_policy"], "informational_only_not_in_plan_totals")
        self.assertEqual(detail.data["item"]["label_nutrition"], {"energy_kcal": "12"})
        self.assertNotIn("user_information", str(detail.data))
        self.assertFalse(foreign.ok)

    @override_settings(SUPPLEMENTS_FEATURE_ENABLED=False)
    def test_pro_gate_blocks_reads_without_leaking_library_state(self):
        result = query_workspace_tool(self.owner, resource="supplements")

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "supplements_pro_required")

    def test_presets_and_plan_intakes_keep_snapshot_identity_and_owner_scope(self):
        plan = DailyPlan.objects.create(name="Plan con tomas", created_by=self.owner, is_draft=False)
        foreign_plan = DailyPlan.objects.create(name="Plan ajeno", created_by=self.other, is_draft=False)
        preset = SupplementIntakePreset.objects.create(created_by=self.owner, name="Toma matinal")
        SupplementIntakePresetItem.objects.create(
            preset=preset,
            supplement=self.owned,
            supplement_snapshot={"name": "Nombre congelado"},
            quantity=1,
            unit="capsule",
        )
        intake = SupplementIntake.objects.create(dailyplan=plan)
        SupplementIntakeItem.objects.create(
            intake=intake,
            supplement=self.owned,
            supplement_snapshot={"name": "Nombre del plan"},
            quantity=2,
            unit="capsule",
        )
        SupplementIntake.objects.create(dailyplan=plan)

        with patch("notas.application.ai_tools.supplement_read_tools.require_supplements_pro"):
            presets = query_workspace_tool(self.owner, resource="supplement_presets")
            intakes = query_workspace_tool(self.owner, resource="supplement_intakes", object_id=plan.id)
            first_page = query_workspace_tool(self.owner, resource="supplement_intakes", object_id=plan.id, limit=1)
            foreign = query_workspace_tool(self.owner, resource="supplement_intakes", object_id=foreign_plan.id)

        self.assertEqual(presets.data["items"][0]["supplements"][0]["name"], "Nombre congelado")
        self.assertEqual(intakes.data["items"][0]["supplements"][0]["name"], "Nombre del plan")
        self.assertEqual(intakes.data["nutrition_policy"], "informational_only_not_in_plan_totals")
        self.assertEqual(first_page.data["total_count"], 2)
        self.assertEqual(first_page.data["returned_count"], 1)
        self.assertTrue(first_page.data["has_more"])
        self.assertFalse(foreign.ok)

    def test_provider_can_query_supplements_but_mutations_go_to_ui(self):
        spec = get_tool_spec("query_workspace")
        self.assertIn("supplements", spec.input_schema["properties"]["resource"]["enum"])
        read = infer_active_work(None, current_user_message="Muéstrame mis suplementos")
        change = infer_active_work(None, current_user_message="Agrega un suplemento a mi plan")
        self.assertEqual(read["expected_outcome"], "workspace_query")
        self.assertEqual(read["resource"], "supplements")
        self.assertEqual(change["action"], "handoff")
        self.assertEqual(change["expected_outcome"], "response_only")
        mixed = infer_active_work(None, current_user_message="Crea una comida con un suplemento")
        self.assertEqual(mixed["action"], "handoff")
