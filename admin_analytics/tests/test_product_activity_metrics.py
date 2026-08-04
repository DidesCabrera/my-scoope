from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from admin_analytics.selectors.product_activity import get_product_activity_metrics
from notas.domain.model_modules.comparisons import SavedComparison
from notas.domain.model_modules.proposals import NutritionProposal
from notas.domain.model_modules.sharing import DailyPlanShare, MealShare, ProgramShare
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood, Program, ProgramDay


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminAnalyticsProductActivityMetricsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="password123",
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username="member@example.com",
            email="member@example.com",
            password="password123",
        )
        self.other_member = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="password123",
        )

    def _build_product_activity_data(self):
        food = Food.objects.create(
            name="Arroz",
            protein=2.0,
            carbs=28.0,
            fat=0.2,
            created_by=self.member,
            is_global=True,
            is_verified=True,
        )
        meal = Meal.objects.create(name="Meal base", created_by=self.member, is_draft=False, is_public=True)
        MealFood.objects.create(meal=meal, food=food, quantity=120)

        dailyplan = DailyPlan.objects.create(
            name="Plan base",
            created_by=self.member,
            source=DailyPlan.SOURCE_AI,
            is_draft=False,
        )
        DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=meal)

        program = Program.objects.create(name="Programa base", created_by=self.member, duration_weeks=2, is_draft=False)
        ProgramDay.objects.create(program=program, dailyplan=dailyplan, week_number=1, day_number=1)
        ProgramDay.objects.create(program=program, dailyplan=dailyplan, week_number=2, day_number=1)

        DailyPlanShare.objects.create(
            sender=self.member,
            recipient_email="other@example.com",
            accepted_by=self.other_member,
            dailyplan=dailyplan,
            is_favorite=True,
        )
        MealShare.objects.create(sender=self.member, recipient_email="friend@example.com", meal=meal)
        ProgramShare.objects.create(sender=self.member, recipient_email="coach@example.com", program=program)

        SavedComparison.objects.create(owner=self.member, kind=SavedComparison.KIND_MEALS, name="Comparar meals")
        proposal = NutritionProposal.objects.create(
            created_by=self.member,
            applied_by=self.member,
            status=NutritionProposal.STATUS_APPLIED,
            source=NutritionProposal.SOURCE_AI,
            title="Propuesta aplicada",
        )
        NutritionProposal.objects.filter(pk=proposal.pk).update(applied_at=food.created_at)

    def test_selector_returns_notas_product_activity_metrics(self):
        self._build_product_activity_data()

        metrics = get_product_activity_metrics()

        self.assertEqual(metrics["north_star"]["weekly_active_nutrition_builders"], 1)
        self.assertEqual(metrics["entities"]["foods"]["total"], 1)
        self.assertEqual(metrics["entities"]["foods"]["global"], 1)
        self.assertEqual(metrics["entities"]["foods"]["verified"], 1)
        self.assertEqual(metrics["entities"]["meals"]["total"], 1)
        self.assertEqual(metrics["entities"]["meals"]["with_foods"], 1)
        self.assertEqual(metrics["entities"]["dailyplans"]["total"], 1)
        self.assertEqual(metrics["entities"]["dailyplans"]["with_meals"], 1)
        self.assertEqual(metrics["entities"]["programs"]["with_slots"], 1)
        self.assertEqual(metrics["entities"]["programs"]["with_multiple_weeks"], 1)
        self.assertEqual(metrics["composition"]["meal_foods_total"], 1)
        self.assertEqual(metrics["composition"]["dailyplan_meals_total"], 1)
        self.assertEqual(metrics["composition"]["program_days_total"], 2)
        self.assertEqual(metrics["comparisons"]["total"], 1)
        self.assertEqual(metrics["shares"]["sent_7d"], 3)
        self.assertEqual(metrics["shares"]["accepted_total"], 1)
        self.assertEqual(metrics["proposals"]["applied_7d"], 1)
        self.assertEqual(metrics["north_star"]["top_builder_rows"][0]["email"], "member@example.com")

    def test_product_activity_dashboard_is_staff_only_and_renders_metrics(self):
        self._build_product_activity_data()

        response = self.client.get(reverse("admin_analytics_product_activity"))
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin_analytics_product_activity"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Product Activity Analytics")
        self.assertContains(response, "Actividad nutricional")
        self.assertContains(response, "Top usuarios por actividad nutricional")
        self.assertContains(response, "Origen de planes diarios")
        self.assertContains(response, "Intercambio nutricional")
        self.assertContains(response, "member@example.com")
