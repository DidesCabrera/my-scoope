from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import AccountPlan, AccountSubscription
from accounts.seed_plans import seed_account_plans
from notas.application.commercial.limits import (
    CommercialLimitReached,
    require_new_program_week,
    require_new_workspace_item,
    require_program_duration,
)
from notas.application.services.commands.meal_commands import create_draft_meal
from notas.domain.models import DailyPlan, Meal, Program, SavedComparison


class CommercialWorkspaceLimitsTests(TestCase):
    def setUp(self):
        seed_account_plans()
        self.user = get_user_model().objects.create_user(username="commercial-limits")

    def test_free_meal_creation_stops_at_twelve_without_deleting_existing(self):
        for number in range(12):
            Meal.objects.create(name=f"Comida {number}", created_by=self.user)
        with self.assertRaisesRegex(CommercialLimitReached, "max_meals_reached"):
            create_draft_meal(user=self.user, name="Otra comida")
        self.assertEqual(Meal.objects.filter(created_by=self.user).count(), 12)
        AccountSubscription.objects.update_or_create(
            user=self.user, defaults={"plan": AccountPlan.objects.get(slug="basic")},
        )
        create_draft_meal(user=self.user, name="Comida pagada")
        AccountSubscription.objects.update_or_create(
            user=self.user, defaults={"plan": AccountPlan.objects.get(slug="free")},
        )
        self.assertEqual(Meal.objects.filter(created_by=self.user).count(), 13)
        with self.assertRaises(CommercialLimitReached):
            create_draft_meal(user=self.user, name="Comida tras downgrade")

    def test_free_dailyplans_programs_comparisons_and_duration(self):
        for number in range(4):
            DailyPlan.objects.create(name=f"Día {number}", created_by=self.user)
        Program.objects.create(name="Programa", created_by=self.user)
        with self.assertRaisesRegex(CommercialLimitReached, "max_dailyplans_reached"):
            require_new_workspace_item(self.user, "dailyplan")
        with self.assertRaisesRegex(CommercialLimitReached, "max_programs_reached"):
            require_new_workspace_item(self.user, "program")
        with self.assertRaisesRegex(CommercialLimitReached, "max_saved_comparisons_reached"):
            require_new_workspace_item(self.user, "comparison")
        with self.assertRaisesRegex(CommercialLimitReached, "max_program_duration_days_reached"):
            require_program_duration(self.user, 3)

    def test_long_program_survives_downgrade_but_cannot_be_extended(self):
        AccountSubscription.objects.update_or_create(
            user=self.user, defaults={"plan": AccountPlan.objects.get(slug="basic")},
        )
        program = Program.objects.create(name="Programa largo", created_by=self.user, duration_weeks=12)
        AccountSubscription.objects.update_or_create(
            user=self.user, defaults={"plan": AccountPlan.objects.get(slug="free")},
        )
        self.assertEqual(Program.objects.get(pk=program.pk).duration_weeks, 12)
        with self.assertRaisesRegex(CommercialLimitReached, "max_program_duration_days_reached"):
            require_new_program_week(program)
