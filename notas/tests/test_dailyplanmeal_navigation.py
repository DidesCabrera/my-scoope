from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from notas.domain.models import DailyPlan, DailyPlanMeal, Meal, Program, ProgramDay

User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class DailyPlanMealNavigationTests(TestCase):

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

        self.meal = Meal.objects.create(
            name="Meal Test",
            created_by=self.user,
            is_draft=False,
            is_public=False,
            is_forkable=True,
            is_copiable=False,
        )

        self.dpm = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=self.meal,
            order=1,
        )

    def test_dailyplan_meal_detail_sets_back_url_to_parent_dailyplan(self):
        response = self.client.get(
            reverse(
                "dailyplan_meal_detail",
                args=[self.dailyplan.id, self.dpm.id],
            )
        )

        self.assertEqual(response.status_code, 200)

        expected_back_url = reverse(
            "dailyplan_detail",
            args=[self.dailyplan.id],
        )

        self.assertEqual(
            response.context["vm"]["ui"]["back_url"],
            expected_back_url,
        )

    def test_dailyplan_meal_back_preserves_program_context(self):
        program = Program.objects.create(
            name="Programa contextual",
            created_by=self.user,
            duration_weeks=2,
        )
        program_day = ProgramDay.objects.create(
            program=program,
            dailyplan=self.dailyplan,
            week_number=2,
            day_number=1,
        )

        response = self.client.get(
            reverse("dailyplan_meal_detail", args=[self.dailyplan.id, self.dpm.id]),
            {"program_day": program_day.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["vm"]["ui"]["back_url"],
            f"{reverse('dailyplan_detail', args=[self.dailyplan.id])}?program_day={program_day.id}",
        )
