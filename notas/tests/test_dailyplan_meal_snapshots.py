from django.contrib.auth import get_user_model
from django.test import TestCase

from notas.application.services.commands.meal_commands import fork_meal
from notas.domain.models import DailyPlan, DailyPlanMeal, Meal

User = get_user_model()


class DailyPlanMealSnapshotTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@test.com",
            password="12345678",
        )

    def test_dailyplan_meal_can_hold_a_snapshot_meal(self):
        original_meal = Meal.objects.create(
            name="Original meal",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        dailyplan = DailyPlan.objects.create(
            name="Plan 1",
            created_by=self.user,
            is_draft=False,
        )

        snapshot_meal = fork_meal(original_meal, self.user)

        dpm = DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=snapshot_meal,
            order=1,
        )

        self.assertNotEqual(dpm.meal.id, original_meal.id)
        self.assertEqual(dpm.meal.forked_from, original_meal)
        self.assertEqual(dpm.meal.created_by, self.user)
        self.assertEqual(dpm.dailyplan, dailyplan)

    def test_editing_slot_metadata_does_not_create_another_meal_snapshot(self):
        original_meal = Meal.objects.create(
            name="Original meal",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        dailyplan = DailyPlan.objects.create(
            name="Plan 1",
            created_by=self.user,
            is_draft=False,
        )

        snapshot_meal = fork_meal(original_meal, self.user)

        dpm = DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=snapshot_meal,
            note="Old note",
            order=1,
        )

        meal_count_before = Meal.objects.count()
        original_snapshot_meal_id = dpm.meal_id

        dpm.note = "Updated note"
        dpm.order = 2
        dpm.save()

        dpm.refresh_from_db()

        self.assertEqual(Meal.objects.count(), meal_count_before)
        self.assertEqual(dpm.meal_id, original_snapshot_meal_id)
        self.assertEqual(dpm.note, "Updated note")
        self.assertEqual(dpm.order, 2)

    def test_replacing_slot_meal_with_new_snapshot_keeps_isolation(self):
        original_meal_a = Meal.objects.create(
            name="Meal A",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        original_meal_b = Meal.objects.create(
            name="Meal B",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        dailyplan = DailyPlan.objects.create(
            name="Plan 1",
            created_by=self.user,
            is_draft=False,
        )

        snapshot_a = fork_meal(original_meal_a, self.user)

        dpm = DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=snapshot_a,
            order=1,
        )

        old_snapshot_id = dpm.meal_id

        replacement_snapshot = fork_meal(original_meal_b, self.user)
        dpm.meal = replacement_snapshot
        dpm.save()

        dpm.refresh_from_db()

        self.assertNotEqual(dpm.meal_id, old_snapshot_id)
        self.assertNotEqual(dpm.meal_id, original_meal_b.id)
        self.assertEqual(dpm.meal.forked_from, original_meal_b)
        self.assertEqual(dpm.meal.created_by, self.user)