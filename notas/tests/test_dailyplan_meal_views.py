from datetime import time

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

    def test_change_time_action_updates_only_the_slot_and_preserves_its_note(self):
        meal = Meal.objects.create(
            name="Desayuno",
            created_by=self.user,
            is_draft=False,
        )
        dpm = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=meal,
            hour=time(8),
            note="Antes de entrenar",
            order=1,
        )
        change_url = reverse("dailyplanmeal_change_time", args=[self.dailyplan.id, dpm.id])
        detail_url = reverse("dailyplan_meal_detail", args=[self.dailyplan.id, dpm.id])

        detail = self.client.get(detail_url)
        form = self.client.get(change_url)
        updated = self.client.post(
            change_url,
            {"hour": "09:35", "note": "Este campo legacy debe ignorarse"},
        )

        self.assertContains(detail, "Cambiar hora")
        self.assertContains(detail, change_url)
        self.assertContains(detail, "entity-heading__subtitle--time")
        self.assertContains(detail, "08:00")
        self.assertEqual(
            detail.context["vm"]["content"]["main_card"]["titulo"]["subtitle"],
            {"text": "08:00", "icon": "clock-3", "modifier": "time"},
        )
        self.assertContains(form, "Hora de la comida")
        self.assertContains(form, 'value="08:00"')
        self.assertNotContains(form, 'name="note"')
        self.assertEqual(list(form.context["form"].fields), ["hour"])
        action_keys = [
            action["key"]
            for action in detail.context["vm"]["content"]["header"]["actions"]
        ]
        self.assertEqual(
            action_keys,
            [
                "back_dp_detail",
                "change_time",
                "rename",
                "share",
                "save_to_library",
                "replace",
            ],
        )
        self.assertRedirects(updated, detail_url)
        dpm.refresh_from_db()
        self.assertEqual(dpm.hour, time(9, 35))
        self.assertEqual(dpm.note, "Antes de entrenar")

    def test_change_time_rejects_invalid_hour_and_ignores_legacy_note_field(self):
        meal = Meal.objects.create(name="Cena", created_by=self.user, is_draft=False)
        dpm = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=meal,
            hour=time(20),
            note="Nota que debe conservarse",
            order=1,
        )
        change_url = reverse("dailyplanmeal_change_time", args=[self.dailyplan.id, dpm.id])

        response = self.client.post(
            change_url,
            {"hour": "hora-inválida", "note": "Intento de cambio"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecciona una hora válida")
        dpm.refresh_from_db()
        self.assertEqual(dpm.hour, time(20))
        self.assertEqual(dpm.note, "Nota que debe conservarse")

    def test_legacy_dailyplan_meal_edit_route_is_removed(self):
        meal = Meal.objects.create(name="Colación", created_by=self.user, is_draft=False)
        dpm = DailyPlanMeal.objects.create(dailyplan=self.dailyplan, meal=meal, order=1)

        response = self.client.get(
            f"/dailyplans/{self.dailyplan.id}/meals/{dpm.id}/edit/",
        )

        self.assertEqual(response.status_code, 404)

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
