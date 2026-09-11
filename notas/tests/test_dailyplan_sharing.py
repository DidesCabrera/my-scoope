from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.sharing.contracts import SHARE_SNAPSHOT_SCHEMA_VERSION
from notas.application.sharing.dailyplans import (
    DailyPlanShareError,
    build_dailyplan_share_snapshot,
    create_dailyplan_share_resource,
)
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood, ShareResource


class DailyPlanSharingAdapterTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("sharing-owner", email="owner@example.com")
        self.plan = DailyPlan.objects.create(name="Plan portable", created_by=self.owner, is_draft=False)
        meal = Meal.objects.create(name="Desayuno", created_by=self.owner, is_draft=False)
        food = Food.objects.create(name="Avena", protein=10, carbs=20, fat=5, created_by=self.owner)
        MealFood.objects.create(meal=meal, food=food, quantity=50)
        DailyPlanMeal.objects.create(dailyplan=self.plan, meal=meal, hour="08:30", note="nota privada")

    def test_snapshot_is_versioned_portable_and_privacy_limited(self):
        snapshot = build_dailyplan_share_snapshot(self.plan)

        self.assertEqual(snapshot["schema_version"], SHARE_SNAPSHOT_SCHEMA_VERSION)
        self.assertEqual(snapshot["subject"], {"type": "daily_plan", "title": "Plan portable"})
        self.assertEqual(snapshot["summary"], {"meal_count": 1, "food_count": 1})
        self.assertEqual(snapshot["nutrition"]["calories"], 82.5)
        self.assertEqual(snapshot["meals"][0]["time"], "08:30")
        serialized = str(snapshot)
        self.assertNotIn("sharing-owner", serialized)
        self.assertNotIn("owner@example.com", serialized)
        self.assertNotIn("nota privada", serialized)
        self.assertNotIn("id", snapshot["subject"])
        self.assertNotIn("id", snapshot["meals"][0])
        self.assertNotIn("id", snapshot["meals"][0]["foods"][0])

    def test_resource_keeps_snapshot_when_source_changes(self):
        result = create_dailyplan_share_resource(sender=self.owner, dailyplan_id=self.plan.id)
        original_snapshot = result.resource.snapshot

        self.plan.name = "Plan editado"
        self.plan.save(update_fields=["name"])
        result.resource.refresh_from_db()

        self.assertEqual(result.resource.snapshot, original_snapshot)
        self.assertEqual(result.resource.snapshot["subject"]["title"], "Plan portable")
        self.assertEqual(result.resource.subject_type, ShareResource.SubjectType.DAILY_PLAN)

    def test_resource_cannot_be_created_from_another_users_plan(self):
        outsider = User.objects.create_user("sharing-outsider")

        with self.assertRaisesMessage(DailyPlanShareError, "dailyplan_share_not_available"):
            create_dailyplan_share_resource(sender=outsider, dailyplan_id=self.plan.id)
