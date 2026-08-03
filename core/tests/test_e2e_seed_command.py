from __future__ import annotations

import json
from io import StringIO

from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.test import TestCase

from notas.domain.models import DailyPlan, DailyPlanMeal, Meal, MealFood


class E2ESeedCommandTests(TestCase):
    def test_seed_is_idempotent_and_emits_owned_fixture_ids(self):
        first_output = StringIO()
        second_output = StringIO()

        call_command(
            "seed_e2e_fixtures",
            "--login",
            "browser@example.test",
            "--password",
            "test-only-password",
            stdout=first_output,
        )
        call_command(
            "seed_e2e_fixtures",
            "--login",
            "browser@example.test",
            "--password",
            "test-only-password",
            stdout=second_output,
        )

        first = json.loads(first_output.getvalue())
        second = json.loads(second_output.getvalue())
        self.assertEqual(first, second)
        user = get_user_model().objects.get(username="browser@example.test")
        self.assertEqual(authenticate(username=user.username, password="test-only-password"), user)
        self.assertTrue(Meal.objects.filter(pk=first["MYSCOOPE_E2E_MEAL_ID"], created_by=user).exists())
        self.assertTrue(DailyPlan.objects.filter(pk=first["MYSCOOPE_E2E_DAILYPLAN_ID"], created_by=user).exists())
        self.assertTrue(
            DailyPlanMeal.objects.filter(
                pk=first["MYSCOOPE_E2E_DAILYPLAN_MEAL_ID"],
                dailyplan__created_by=user,
            ).exists()
        )
        self.assertGreaterEqual(
            MealFood.objects.filter(meal_id=first["MYSCOOPE_E2E_MEAL_ID"]).count(),
            5,
        )

