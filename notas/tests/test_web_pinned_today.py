import uuid

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription
from accounts.seed_plans import seed_account_plans
from notas.application.services.commands.supplement_commands import create_supplement_intake
from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Meal,
    PinnedDailyPlan,
    PinnedDailyPlanMealExecution,
    PinnedSupplementIntakeExecution,
    ProgramCalendarization,
    Supplement,
)


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False, SUPPLEMENTS_FEATURE_ENABLED=True)
class WebPinnedTodayTests(TestCase):
    def setUp(self):
        seed_account_plans()
        self.user = User.objects.create_user(username="pinned-web", password="secret")
        AccountSubscription.objects.update_or_create(
            user=self.user, defaults={"plan": AccountPlan.objects.get(slug="pro")},
        )
        self.client.force_login(self.user)

    def test_create_pin_and_check_in_meal_and_supplement(self):
        response = self.client.get(reverse("home_view"))
        self.assertContains(response, "Crear un plan para hoy")
        self.assertContains(response, "home-stat-card__surface-link", count=6)
        response = self.client.post(reverse("home_create_pinned_dailyplan"))
        self.assertEqual(response.status_code, 302)
        pinned = PinnedDailyPlan.objects.get(user=self.user)
        self.assertTrue(pinned.is_active)
        self.assertContains(self.client.get(reverse("home_view")), pinned.dailyplan.name)

        meal = Meal.objects.create(name="Cena", created_by=self.user)
        relation = DailyPlanMeal.objects.create(dailyplan=pinned.dailyplan, meal=meal, order=1)
        supplement = Supplement.objects.create(created_by=self.user, name="Vitamina")
        intake = create_supplement_intake(
            user=self.user, dailyplan_id=pinned.dailyplan_id,
            items=[{"supplement_id": supplement.id, "quantity": 1, "unit": "capsule"}],
        )
        home = self.client.get(reverse("home_view"))
        self.assertContains(home, "Cena")
        self.assertContains(home, "Vitamina")
        key = str(uuid.uuid4())
        response = self.client.post(reverse("home_pinned_meal_check_in", args=[relation.id]), {
            "action": "completed", "idempotency_key": key,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PinnedDailyPlanMealExecution.objects.get().action, "completed")
        response = self.client.post(reverse("home_pinned_supplement_check_in", args=[intake.id]), {
            "action": "completed", "idempotency_key": str(uuid.uuid4()),
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PinnedSupplementIntakeExecution.objects.get().action, "completed")
        self.assertContains(self.client.get(reverse("home_view")), "completada", count=2)
        self.client.post(reverse("home_unpin_dailyplan"))
        pinned.refresh_from_db()
        self.assertFalse(pinned.is_active)

    def test_pin_existing_plan_and_reject_foreign_plan_or_meal(self):
        plan = DailyPlan.objects.create(name="Mi Minuta", created_by=self.user)
        self.assertEqual(self.client.post(reverse("home_pin_dailyplan"), {
            "dailyplan_id": plan.id,
        }).status_code, 302)
        self.assertEqual(PinnedDailyPlan.objects.get(user=self.user).dailyplan_id, plan.id)
        other = User.objects.create_user(username="other-pinned", password="secret")
        other_plan = DailyPlan.objects.create(name="Privada", created_by=other)
        self.client.post(reverse("home_pin_dailyplan"), {"dailyplan_id": other_plan.id})
        self.assertEqual(PinnedDailyPlan.objects.get(user=self.user).dailyplan_id, plan.id)
        self.assertEqual(self.client.post(reverse("home_pinned_meal_check_in", args=[99999]), {
            "action": "completed", "idempotency_key": str(uuid.uuid4()),
        }).status_code, 302)
        self.assertFalse(PinnedDailyPlanMealExecution.objects.exists())

    def test_active_program_blocks_new_pinned_plan(self):
        today = timezone.localdate()
        ProgramCalendarization.objects.create(
            user=self.user, program_name_snapshot="Programa",
            start_date=today, end_date=today, timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        self.assertEqual(self.client.post(reverse("home_create_pinned_dailyplan")).status_code, 404)
        self.assertFalse(PinnedDailyPlan.objects.filter(user=self.user).exists())
