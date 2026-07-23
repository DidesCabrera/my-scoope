from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from notas.domain.models import DailyPlan, Meal


User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class DailyPlanViewTests(TestCase):

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

    def test_dailyplan_create_creates_draft_dailyplan(self):
        response = self.client.post(
            reverse("dailyplan_create"),
            data={
                "name": "New plan",
            },
        )

        self.assertEqual(response.status_code, 302)

        dailyplan = DailyPlan.objects.get(name="New plan")

        self.assertEqual(dailyplan.created_by, self.user)
        self.assertTrue(dailyplan.is_draft)

    def test_dailyplan_rename_updates_name(self):
        dailyplan = DailyPlan.objects.create(
            name="Old plan name",
            created_by=self.user,
            is_draft=False,
        )

        response = self.client.post(
            reverse("dailyplan_rename", args=[dailyplan.id]),
            data={
                "name": "New plan name",
            },
        )

        self.assertEqual(response.status_code, 302)

        dailyplan.refresh_from_db()
        self.assertEqual(dailyplan.name, "New plan name")

    def test_dailyplan_remove_deletes_dailyplan(self):
        dailyplan = DailyPlan.objects.create(
            name="Plan to remove",
            created_by=self.user,
            is_draft=False,
        )

        response = self.client.post(
            reverse("dailyplan_remove", args=[dailyplan.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(DailyPlan.objects.filter(id=dailyplan.id).exists())

    def test_dailyplan_fork_creates_new_plan_for_logged_user(self):
        author = User.objects.create_user(
            username="author",
            email="author@test.com",
            password="12345678",
        )

        meal = Meal.objects.create(
            name="Original meal",
            created_by=author,
            is_draft=False,
            is_public=True,
            is_forkable=True,
            is_copiable=False,
        )

        original = DailyPlan.objects.create(
            name="Original plan",
            created_by=author,
            is_draft=False,
            is_public=True,
            is_forkable=True,
            is_copiable=False,
        )

        original.dailyplan_meals.create(
            meal=meal,
            order=1,
        )

        response = self.client.post(
            reverse("dailyplan_fork", args=[original.id])
        )

        self.assertEqual(response.status_code, 302)

        forked = DailyPlan.objects.exclude(id=original.id).get()

        self.assertEqual(forked.created_by, self.user)
        self.assertEqual(forked.forked_from, original)
        self.assertEqual(forked.original_author, author)
        self.assertEqual(forked.dailyplan_meals.count(), 1)

        forked_dpm = forked.dailyplan_meals.first()
        self.assertNotEqual(forked_dpm.meal.id, meal.id)
        self.assertEqual(forked_dpm.meal.forked_from, meal)

    def test_dailyplan_configure_redirects_when_user_has_no_distribution_access(self):
        dailyplan = DailyPlan.objects.create(
            name="Config plan",
            created_by=self.user,
            is_draft=False,
        )

        response = self.client.get(
            reverse("dailyplan_configure", args=[dailyplan.id])
        )

        self.assertEqual(response.status_code, 302)

        dailyplan.refresh_from_db()
        self.assertFalse(dailyplan.is_public)
        self.assertTrue(dailyplan.is_forkable)
        self.assertFalse(dailyplan.is_copiable)

