from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from notas.domain.models import ProgramCalendarization


class AppReviewDemoCommandTests(TestCase):
    def test_prepares_existing_account_idempotently_without_a_committed_secret(self):
        user = User.objects.create_user(username="reviewer@example.com", password="not-stored-by-command")

        first_output = StringIO()
        call_command("prepare_app_review_demo", login=user.username, stdout=first_output)
        second_output = StringIO()
        call_command("prepare_app_review_demo", login=user.username, stdout=second_output)

        calendarization = ProgramCalendarization.objects.get(user=user)
        self.assertEqual(calendarization.days.count(), 7)
        self.assertTrue(all(day.plan_snapshot for day in calendarization.days.all()))
        self.assertIn("Demo ready", first_output.getvalue())
        self.assertIn("Demo already ready", second_output.getvalue())
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.mobile_disclosure_version, user.profile.MOBILE_DISCLOSURE_VERSION)
