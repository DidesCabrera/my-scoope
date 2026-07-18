from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from notas.domain.models import DailyPlan, DailyPlanMeal, Meal


User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class DailyPlanMealViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@test.com",
            password="12345678",
        )

        self.client = Client()
        self.client.login(
            username="felipe",
            password="12345678",
        )

        self.dailyplan = DailyPlan.objects.create(
            name="Plan 1",
            created_by=self.user,
            is_draft=False,
        )

    def test_dailyplan_add_meal_creates_snapshot_instead_of_linking_original(self):
        original_meal = Meal.objects.create(
            name="Original meal",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        response = self.client.post(
            reverse("dailyplan_add_meal", args=[self.dailyplan.id]),
            data={
                "dailyplan_id": self.dailyplan.id,
                "meal_id": original_meal.id,
                "hour": "08:30",
                "note": "Breakfast slot",
            },
        )

        self.assertEqual(response.status_code, 302)

        dpm = DailyPlanMeal.objects.get(dailyplan=self.dailyplan)

        self.assertNotEqual(dpm.meal.id, original_meal.id)
        self.assertEqual(dpm.meal.forked_from, original_meal)
        self.assertEqual(dpm.meal.created_by, self.user)
        self.assertEqual(dpm.note, "Breakfast slot")
        self.assertIsNotNone(dpm.hour)

    def test_dailyplanmeal_edit_updates_slot_metadata_without_replacing_meal(self):
        original_meal = Meal.objects.create(
            name="Original meal",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        dpm = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=original_meal,
            note="Old note",
            order=1,
        )

        original_meal_id = dpm.meal_id

        response = self.client.post(
            reverse("dailyplan_meal_edit", args=[self.dailyplan.id, dpm.id]),
            data={
                "hour": "10:15",
                "note": "Updated note",
            },
        )

        self.assertEqual(response.status_code, 302)

        dpm.refresh_from_db()

        self.assertEqual(dpm.meal_id, original_meal_id)
        self.assertEqual(dpm.note, "Updated note")
        self.assertIsNotNone(dpm.hour)

    def test_dailyplanmeal_update_replaces_slot_with_new_snapshot(self):
        meal_a = Meal.objects.create(
            name="Meal A",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        meal_b = Meal.objects.create(
            name="Meal B",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        dpm = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=meal_a,
            note="Initial note",
            order=1,
        )

        old_meal_id = dpm.meal_id

        response = self.client.post(
            reverse("dailyplanmeal_update", args=[self.dailyplan.id, dpm.id]),
            data={
                "meal_id": meal_b.id,
                "hour": "13:00",
                "note": "Lunch replacement",
            },
        )

        self.assertEqual(response.status_code, 302)

        dpm.refresh_from_db()

        self.assertNotEqual(dpm.meal_id, old_meal_id)
        self.assertNotEqual(dpm.meal_id, meal_b.id)
        self.assertEqual(dpm.meal.forked_from, meal_b)
        self.assertEqual(dpm.meal.created_by, self.user)
        self.assertEqual(dpm.note, "Lunch replacement")
        self.assertIsNotNone(dpm.hour)

    def test_dailyplanmeal_update_with_same_meal_does_not_create_new_snapshot(self):
        original_meal = Meal.objects.create(
            name="Meal A",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        dpm = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=original_meal,
            note="Initial note",
            order=1,
        )

        meal_count_before = Meal.objects.count()
        original_meal_id = dpm.meal_id

        response = self.client.post(
            reverse("dailyplanmeal_update", args=[self.dailyplan.id, dpm.id]),
            data={
                "meal_id": original_meal.id,
                "hour": "14:00",
                "note": "Only metadata changed",
            },
        )

        self.assertEqual(response.status_code, 302)

        dpm.refresh_from_db()

        self.assertEqual(Meal.objects.count(), meal_count_before)
        self.assertEqual(dpm.meal_id, original_meal_id)
        self.assertEqual(dpm.note, "Only metadata changed")
        self.assertIsNotNone(dpm.hour)

    def test_dailyplanmeal_remove_deletes_slot_and_its_meal(self):
        meal = Meal.objects.create(
            name="Snapshot meal",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        dpm = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=meal,
            order=1,
        )

        meal_id = meal.id
        dpm_id = dpm.id

        response = self.client.post(
            reverse("dailyplanmeal_remove", args=[self.dailyplan.id, dpm.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(DailyPlanMeal.objects.filter(id=dpm_id).exists())
        self.assertFalse(Meal.objects.filter(id=meal_id).exists())
