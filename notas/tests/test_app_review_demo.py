from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from notas.domain.models import DailyPlan, ProgramCalendarization


class AppReviewDemoCommandTests(TestCase):
    def test_prepares_existing_account_idempotently_without_a_committed_secret(self):
        user = User.objects.create_user(username="reviewer@example.com", password="not-stored-by-command")

        first_output = StringIO()
        call_command("prepare_app_review_demo", login=user.username, stdout=first_output)
        second_output = StringIO()
        call_command("prepare_app_review_demo", login=user.username, stdout=second_output)

        calendarization = ProgramCalendarization.objects.get(user=user)
        daily_plan = DailyPlan.objects.get(created_by=user, name="Día de fuerza · revisión")
        self.assertEqual(calendarization.days.count(), 7)
        self.assertEqual(daily_plan.dailyplan_meals.count(), 4)
        self.assertTrue(all(day.plan_snapshot for day in calendarization.days.all()))
        self.assertIn("Demo ready", first_output.getvalue())
        self.assertIn("Demo already ready", second_output.getvalue())
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.mobile_disclosure_version, user.profile.MOBILE_DISCLOSURE_VERSION)

        for day in calendarization.days.all():
            snapshot = dict(day.plan_snapshot)
            snapshot["meals"] = snapshot["meals"][:2]
            day.plan_snapshot = snapshot
            day.save(update_fields=["plan_snapshot"])

        refresh_output = StringIO()
        call_command("prepare_app_review_demo", login=user.username, stdout=refresh_output)

        refreshed = ProgramCalendarization.objects.get(user=user, status="active")
        self.assertNotEqual(refreshed.id, calendarization.id)
        self.assertTrue(all(len(day.plan_snapshot["meals"]) == 4 for day in refreshed.days.all()))
        self.assertIn("Demo refreshed", refresh_output.getvalue())
