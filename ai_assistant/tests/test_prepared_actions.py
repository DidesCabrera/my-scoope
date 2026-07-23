from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from ai_assistant.application.prepared_actions import (
    cancel_prepared_action,
    commit_prepared_action,
    prepare_product_action,
)
from ai_assistant.models import AIPreparedAction
from notas.domain.models import DailyPlan, Meal


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
