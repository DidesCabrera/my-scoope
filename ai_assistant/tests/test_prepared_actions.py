from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from ai_assistant.application.prepared_actions import (
    cancel_prepared_action,
    commit_prepared_action,
    prepare_product_action,
    prepare_workspace_patch,
)
from ai_assistant.models import AIPreparedAction
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class PreparedProductActionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass123")
        self.other_user = User.objects.create_user(username="other", password="pass123")
        self.meal = Meal.objects.create(
            name="Comida original",
            created_by=self.user,
            is_draft=False,
        )

    def test_prepare_preview_does_not_mutate_then_trusted_commit_updates(self):
        action = prepare_product_action(
            user=self.user,
            action_key="meal.rename",
            target_id=self.meal.id,
            parameters={"name": "Comida nueva"},
        )

        self.meal.refresh_from_db()
        self.assertEqual(self.meal.name, "Comida original")
        self.assertEqual(action.preview["before"]["name"], "Comida original")
        self.assertEqual(action.preview["after"]["name"], "Comida nueva")
        self.assertEqual(action.status, AIPreparedAction.Status.PREPARED)

        committed = commit_prepared_action(
            user=self.user,
            public_id=action.public_id,
        )

        self.meal.refresh_from_db()
        self.assertEqual(self.meal.name, "Comida nueva")
        self.assertEqual(committed.status, AIPreparedAction.Status.COMMITTED)
        self.assertEqual(committed.result["meal_id"], self.meal.id)

    def test_other_user_cannot_prepare_or_commit_owned_target(self):
        with self.assertRaisesMessage(ValueError, "prepared_action_meal_not_available"):
            prepare_product_action(
                user=self.other_user,
                action_key="meal.rename",
                target_id=self.meal.id,
                parameters={"name": "Intrusión"},
            )
        action = prepare_product_action(
            user=self.user,
            action_key="meal.rename",
            target_id=self.meal.id,
            parameters={"name": "Permitido"},
        )
        with self.assertRaisesMessage(ValueError, "prepared_action_not_found"):
            commit_prepared_action(
                user=self.other_user,
                public_id=action.public_id,
            )

    def test_commit_blocks_stale_preview(self):
        action = prepare_product_action(
            user=self.user,
            action_key="meal.rename",
            target_id=self.meal.id,
            parameters={"name": "Nombre preparado"},
        )
        self.meal.name = "Cambio humano posterior"
        self.meal.save(update_fields=["name"])

        with self.assertRaisesMessage(ValueError, "prepared_action_target_changed"):
            commit_prepared_action(
                user=self.user,
                public_id=action.public_id,
            )

        self.meal.refresh_from_db()
        self.assertEqual(self.meal.name, "Cambio humano posterior")

    def test_cancelled_destructive_action_never_deletes_target(self):
        action = prepare_product_action(
            user=self.user,
            action_key="meal.delete",
            target_id=self.meal.id,
        )
        self.assertTrue(action.destructive)

        cancelled = cancel_prepared_action(
            user=self.user,
            public_id=action.public_id,
        )

        self.assertEqual(cancelled.status, AIPreparedAction.Status.CANCELLED)
        self.assertTrue(Meal.objects.filter(pk=self.meal.id).exists())

    def test_commit_endpoint_requires_post_and_authenticated_owner(self):
        action = prepare_product_action(
            user=self.user,
            action_key="dailyplan.create",
            parameters={"name": "Plan desde acción"},
        )
        url = reverse("ai_prepared_action_commit", args=[action.public_id])

        anonymous = self.client.post(url)
        self.assertEqual(anonymous.status_code, 302)
        self.client.force_login(self.other_user)
        denied = self.client.post(url)
        self.assertEqual(denied.status_code, 302)
        self.assertFalse(DailyPlan.objects.filter(name="Plan desde acción").exists())

        self.client.force_login(self.user)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            DailyPlan.objects.filter(
                created_by=self.user,
                name="Plan desde acción",
            ).exists()
        )

    def test_workspace_patch_previews_and_atomically_commits_multiple_operations(self):
        action = prepare_workspace_patch(
            user=self.user,
            title="Ajustar mi espacio",
            summary="Renombra la comida y crea un plan vacío.",
            operations=[
                {
                    "operation_id": "rename_meal",
                    "resource": "meal",
                    "action": "rename",
                    "target_id": self.meal.id,
                    "parameters": {"name": "Comida del patch"},
                },
                {
                    "operation_id": "create_plan",
                    "resource": "dailyplan",
                    "action": "create",
                    "parameters": {"name": "Plan del patch"},
                },
            ],
        )

        self.meal.refresh_from_db()
        self.assertEqual(self.meal.name, "Comida original")
        self.assertEqual(action.action_key, "workspace.patch")
        self.assertEqual(action.preview["operation_count"], 2)
        self.assertEqual(action.preview["risk_level"], "low")
        self.assertTrue(action.preview["approval_policy"]["future_auto_apply_eligible"])

        committed = commit_prepared_action(user=self.user, public_id=action.public_id)

        self.meal.refresh_from_db()
        self.assertEqual(self.meal.name, "Comida del patch")
        self.assertTrue(DailyPlan.objects.filter(created_by=self.user, name="Plan del patch").exists())
        self.assertTrue(committed.result["atomic"])
        self.assertEqual(committed.result["operation_count"], 2)

    def test_workspace_patch_blocks_all_operations_when_one_preview_is_stale(self):
        action = prepare_workspace_patch(
            user=self.user,
            title="Cambios coordinados",
            summary="Debe fallar completo si el objetivo cambió.",
            operations=[
                {
                    "operation_id": "rename_meal",
                    "resource": "meal",
                    "action": "rename",
                    "target_id": self.meal.id,
                    "parameters": {"name": "Nombre preparado"},
                },
                {
                    "operation_id": "create_plan",
                    "resource": "dailyplan",
                    "action": "create",
                    "parameters": {"name": "No debe existir"},
                },
            ],
        )
        self.meal.name = "Cambio humano"
        self.meal.save(update_fields=["name"])

        with self.assertRaisesMessage(ValueError, "prepared_action_target_changed"):
            commit_prepared_action(user=self.user, public_id=action.public_id)

        self.assertFalse(DailyPlan.objects.filter(created_by=self.user, name="No debe existir").exists())

    def test_workspace_patch_marks_destructive_operation_as_high_risk(self):
        action = prepare_workspace_patch(
            user=self.user,
            title="Eliminar comida",
            summary="Elimina una comida.",
            operations=[
                {
                    "operation_id": "delete_meal",
                    "resource": "meal",
                    "action": "delete",
                    "target_id": self.meal.id,
                    "parameters": {},
                },
            ],
        )

        self.assertTrue(action.destructive)
        self.assertEqual(action.preview["risk_level"], "high")
        self.assertFalse(action.preview["approval_policy"]["future_auto_apply_eligible"])

    def test_workspace_patch_can_compose_owned_meal_with_readable_food(self):
        food = Food.objects.create(
            name="Avena",
            protein=12,
            carbs=60,
            fat=7,
            created_by=self.user,
        )
        action = prepare_workspace_patch(
            user=self.user,
            title="Completar desayuno",
            summary="Agrega avena a la comida.",
            operations=[
                {
                    "operation_id": "add_oats",
                    "resource": "meal",
                    "action": "add_food",
                    "target_id": self.meal.id,
                    "parameters": {"food_id": food.id, "quantity": 80},
                }
            ],
        )

        self.assertFalse(MealFood.objects.filter(meal=self.meal, food=food).exists())
        commit_prepared_action(user=self.user, public_id=action.public_id)

        meal_food = MealFood.objects.get(meal=self.meal, food=food)
        self.assertEqual(float(meal_food.quantity), 80)

    def test_workspace_patch_can_replace_meal_food_and_set_exact_quantity(self):
        original = Food.objects.create(
            name="Arroz",
            protein=3,
            carbs=28,
            fat=0,
            created_by=self.user,
        )
        replacement = Food.objects.create(
            name="Papa",
            protein=2,
            carbs=20,
            fat=0,
            created_by=self.user,
        )
        meal_food = MealFood.objects.create(
            meal=self.meal,
            food=original,
            quantity=100,
        )

        action = prepare_workspace_patch(
            user=self.user,
            title="Cambiar acompañamiento",
            summary="Reemplaza arroz por papa y deja la porción en 200 g.",
            operations=[
                {
                    "operation_id": "replace_rice",
                    "resource": "meal",
                    "action": "update_food",
                    "target_id": meal_food.id,
                    "parameters": {"food_id": replacement.id, "quantity": 200},
                }
            ],
        )

        meal_food.refresh_from_db()
        self.assertEqual(meal_food.food_id, original.id)
        self.assertEqual(float(meal_food.quantity), 100)
        self.assertEqual(action.preview["operations"][0]["after"]["food_id"], replacement.id)
        self.assertEqual(action.preview["operations"][0]["after"]["quantity"], 200)

        commit_prepared_action(user=self.user, public_id=action.public_id)

        meal_food.refresh_from_db()
        self.assertEqual(meal_food.food_id, replacement.id)
        self.assertEqual(float(meal_food.quantity), 200)

    def test_workspace_patch_can_replace_food_using_public_meal_and_food_ids(self):
        original = Food.objects.create(
            name="Arroz",
            protein=3,
            carbs=28,
            fat=0,
            created_by=self.user,
        )
        replacement = Food.objects.create(
            name="Papa",
            protein=2,
            carbs=20,
            fat=0,
            created_by=self.user,
        )
        MealFood.objects.create(meal=self.meal, food=original, quantity=100)

        action = prepare_workspace_patch(
            user=self.user,
            title="Cambiar acompañamiento",
            summary="Reemplaza arroz por papa y deja la porción en 200 g.",
            operations=[
                {
                    "operation_id": "remove_rice",
                    "resource": "meal",
                    "action": "remove_food",
                    "target_id": self.meal.id,
                    "parameters": {"food_id": original.id},
                },
                {
                    "operation_id": "add_potato",
                    "resource": "meal",
                    "action": "add_food",
                    "target_id": self.meal.id,
                    "parameters": {"food_id": replacement.id, "quantity": 200},
                },
            ],
        )

        self.assertTrue(MealFood.objects.filter(meal=self.meal, food=original).exists())
        self.assertFalse(MealFood.objects.filter(meal=self.meal, food=replacement).exists())

        commit_prepared_action(user=self.user, public_id=action.public_id)

        self.assertFalse(MealFood.objects.filter(meal=self.meal, food=original).exists())
        replacement_row = MealFood.objects.get(meal=self.meal, food=replacement)
        self.assertEqual(float(replacement_row.quantity), 200)

    def test_workspace_patch_prefers_explicit_ids_over_redundant_references(self):
        original = Food.objects.create(
            name="Arroz",
            protein=3,
            carbs=28,
            fat=0,
            created_by=self.user,
        )
        replacement = Food.objects.create(
            name="Papa",
            protein=2,
            carbs=20,
            fat=0,
            created_by=self.user,
        )
        MealFood.objects.create(meal=self.meal, food=original, quantity=100)

        action = prepare_workspace_patch(
            user=self.user,
            title="Cambiar acompañamiento",
            summary="Reemplaza arroz por papa y deja la porción en 200 g.",
            operations=[
                {
                    "operation_id": "remove_rice",
                    "resource": "meal",
                    "action": "remove_food",
                    "target_id": self.meal.id,
                    "references": {
                        "target_id": "unused_create",
                        "food_id": "unused_create",
                        "meal_id": None,
                    },
                    "parameters": {"food_id": original.id},
                },
                {
                    "operation_id": "add_potato",
                    "resource": "meal",
                    "action": "add_food",
                    "target_id": self.meal.id,
                    "references": {"target_id": "remove_rice", "food_id": "remove_rice"},
                    "parameters": {"food_id": replacement.id, "quantity": 200},
                },
            ],
        )

        self.assertEqual(action.preview["operations"][0]["references"], {})
        self.assertEqual(action.preview["operations"][1]["references"], {})

        commit_prepared_action(user=self.user, public_id=action.public_id)

        self.assertFalse(MealFood.objects.filter(meal=self.meal, food=original).exists())
        replacement_row = MealFood.objects.get(meal=self.meal, food=replacement)
        self.assertEqual(float(replacement_row.quantity), 200)

    def test_workspace_patch_can_add_owned_meal_to_dailyplan(self):
        dailyplan = DailyPlan.objects.create(
            name="Plan semanal",
            created_by=self.user,
            is_draft=False,
        )
        action = prepare_workspace_patch(
            user=self.user,
            title="Completar plan",
            summary="Agrega la comida al plan diario.",
            operations=[
                {
                    "operation_id": "add_lunch",
                    "resource": "dailyplan",
                    "action": "add_meal",
                    "target_id": dailyplan.id,
                    "parameters": {
                        "meal_id": self.meal.id,
                        "hour": "13:30",
                        "note": "Después de entrenar",
                    },
                }
            ],
        )

        self.assertFalse(DailyPlanMeal.objects.filter(dailyplan=dailyplan).exists())
        commit_prepared_action(user=self.user, public_id=action.public_id)

        dailyplan_meal = DailyPlanMeal.objects.get(dailyplan=dailyplan)
        self.assertNotEqual(dailyplan_meal.meal_id, self.meal.id)
        self.assertEqual(dailyplan_meal.meal.name, self.meal.name)
        self.assertEqual(str(dailyplan_meal.hour), "13:30:00")
        self.assertEqual(dailyplan_meal.note, "Después de entrenar")

    def test_workspace_patch_can_compose_entities_created_by_prior_operations(self):
        action = prepare_workspace_patch(
            user=self.user,
            title="Crear desayuno completo",
            summary="Crea un alimento, una comida y agrega el alimento a la comida.",
            operations=[
                {
                    "operation_id": "create_oats",
                    "resource": "food",
                    "action": "create",
                    "parameters": {
                        "name": "Avena preparada",
                        "protein": 12,
                        "carbs": 60,
                        "fat": 7,
                    },
                },
                {
                    "operation_id": "create_breakfast",
                    "resource": "meal",
                    "action": "create",
                    "parameters": {"name": "Desayuno de avena"},
                },
                {
                    "operation_id": "add_oats",
                    "resource": "meal",
                    "action": "add_food",
                    "references": {
                        "target_id": "create_breakfast",
                        "food_id": "create_oats",
                    },
                    "parameters": {"quantity": 80},
                },
            ],
        )

        self.assertFalse(Food.objects.filter(name="Avena preparada").exists())
        self.assertEqual(
            action.preview["operations"][2]["references"],
            {"target_id": "create_breakfast", "food_id": "create_oats"},
        )

        committed = commit_prepared_action(user=self.user, public_id=action.public_id)

        food = Food.objects.get(created_by=self.user, name="Avena preparada")
        meal = Meal.objects.get(created_by=self.user, name="Desayuno de avena")
        meal_food = MealFood.objects.get(meal=meal, food=food)
        self.assertEqual(float(meal_food.quantity), 80)
        self.assertEqual(committed.result["operation_count"], 3)

    def test_workspace_patch_rejects_forward_operation_reference(self):
        with self.assertRaisesMessage(
            ValueError,
            "workspace_patch_reference_not_available:create_breakfast",
        ):
            prepare_workspace_patch(
                user=self.user,
                title="Referencia inválida",
                summary="No permite referencias futuras.",
                operations=[
                    {
                        "operation_id": "add_food",
                        "resource": "meal",
                        "action": "add_food",
                        "references": {"target_id": "create_breakfast"},
                        "parameters": {"food_id": 1, "quantity": 80},
                    },
                    {
                        "operation_id": "create_breakfast",
                        "resource": "meal",
                        "action": "create",
                        "parameters": {"name": "Desayuno"},
                    },
                ],
            )
