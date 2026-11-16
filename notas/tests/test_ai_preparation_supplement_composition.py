from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from notas.application.ai_tools.prepared_actions import commit_prepared_action, prepare_workspace_patch
from notas.application.ai_tools.workspace_query_tools import query_workspace_tool
from notas.domain.models import DailyPlan, Meal, MealPreparation, Preparation, PreparationVersion, Supplement
from ai_assistant.application.tools.registry import list_provider_tool_specs


class CompositionAssistantTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(username="composition-owner")
        self.other = users.objects.create_user(username="composition-other")
        self.meal = Meal.objects.create(name="Almuerzo", created_by=self.user)
        self.plan = DailyPlan.objects.create(name="Minuta", created_by=self.user)
        self.preparation = Preparation.objects.create(name="Receta", is_global=True)
        version = PreparationVersion.objects.create(
            preparation=self.preparation, version=1, release_version="test",
            yield_g=200, default_portion_g=100, household_label="porción",
            protein_g=10, carbs_g=20, fat_g=5, content_sha256="test",
        )
        self.preparation.current_version = version
        self.preparation.save(update_fields=["current_version"])
        self.supplement = Supplement.objects.create(created_by=self.user, name="Cápsula")

    def test_preparation_read_and_reviewed_meal_composition(self):
        detail = query_workspace_tool(self.user, resource="preparations", object_id=self.preparation.id)
        self.assertTrue(detail.ok)
        self.assertEqual(detail.data["item"]["yield_g"], "200.000")
        foreign = Preparation.objects.create(name="Privada", is_global=False, created_by=self.other)
        self.assertFalse(query_workspace_tool(self.user, resource="preparations", object_id=foreign.id).ok)
        action = prepare_workspace_patch(user=self.user, title="Porción", summary="Agregar receta", operations=[{
            "operation_id": "add", "resource": "meal", "action": "add_preparation",
            "target_id": self.meal.id,
            "parameters": {"preparation_id": self.preparation.id, "units": 1},
        }])
        self.assertFalse(MealPreparation.objects.filter(meal=self.meal).exists())
        commit_prepared_action(user=self.user, public_id=action.public_id)
        relation = MealPreparation.objects.get(meal=self.meal)
        self.assertEqual(relation.quantity_g, 100)
        self.assertEqual(relation.version_id, self.preparation.current_version_id)
        instances = query_workspace_tool(self.user, resource="meal_preparations", object_id=self.meal.id)
        self.assertEqual(instances.data["items"][0]["relation_id"], relation.id)
        change = prepare_workspace_patch(user=self.user, title="Porción", summary="Ajustar receta", operations=[{
            "operation_id": "resize", "resource": "meal", "action": "update_preparation",
            "target_id": relation.id, "parameters": {"grams": 50},
        }])
        commit_prepared_action(user=self.user, public_id=change.public_id)
        relation.refresh_from_db()
        self.assertEqual(relation.quantity_g, 50)

    def test_supplement_patch_keeps_nutrition_out_of_plan_totals(self):
        with patch("notas.application.services.commands.supplement_commands.require_supplements_pro"):
            action = prepare_workspace_patch(user=self.user, title="Toma", summary="Agregar cápsula", operations=[{
                "operation_id": "add", "resource": "dailyplan", "action": "add_supplement_intake",
                "target_id": self.plan.id,
                "parameters": {"items": [{"supplement_id": self.supplement.id, "quantity": 1, "unit": "capsule"}]},
            }])
            self.assertFalse(self.plan.supplement_intakes.exists())
            commit_prepared_action(user=self.user, public_id=action.public_id)
        self.assertEqual(self.plan.supplement_intakes.count(), 1)
        self.assertTrue(action.preview["operations"][0]["after"]["nutrition_totals_unchanged"])
        intake = self.plan.supplement_intakes.get()
        with patch("notas.application.services.commands.supplement_commands.require_supplements_pro"):
            removal = prepare_workspace_patch(user=self.user, title="Quitar", summary="Quitar toma", operations=[{
                "resource": "dailyplan", "action": "remove_supplement_intake", "target_id": intake.id,
                "parameters": {},
            }])
            commit_prepared_action(user=self.user, public_id=removal.public_id)
        self.assertFalse(self.plan.supplement_intakes.exists())

    def test_provider_schema_exposes_typed_composition(self):
        patch_tool = next(item for item in list_provider_tool_specs() if item["name"] == "propose_workspace_patch")
        operation = patch_tool["parameters"]["properties"]["operations"]["items"]["properties"]
        self.assertIn("add_preparation", operation["action"]["enum"])
        self.assertIn("add_supplement_intake", operation["action"]["enum"])
        self.assertIn("items", operation["parameters"]["properties"])

    def test_rejects_other_users_targets_and_invalid_portions(self):
        with self.assertRaises(ValueError):
            prepare_workspace_patch(user=self.other, title="X", summary="X", operations=[{
                "resource": "meal", "action": "add_preparation", "target_id": self.meal.id,
                "parameters": {"preparation_id": self.preparation.id, "grams": 100},
            }])
        with self.assertRaises(ValueError):
            prepare_workspace_patch(user=self.user, title="X", summary="X", operations=[{
                "resource": "meal", "action": "add_preparation", "target_id": self.meal.id,
                "parameters": {"preparation_id": self.preparation.id, "units": 0.3},
            }])
