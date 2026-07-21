from datetime import date, datetime, timezone as dt_timezone
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from notas.domain.models import CalendarizedDay, DailyPlan, ProgramCalendarization


UTC = dt_timezone.utc
FIXED_NOW = datetime(2026, 7, 15, 12, tzinfo=UTC)


class HomeCalendarizationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="home-calendar", password="pw")
        profile = self.user.profile
        profile.onboarding_completed_at = FIXED_NOW
        profile.onboarding_version = profile.ONBOARDING_VERSION_NUTRITION_V1
        profile.timezone_name = "UTC"
        profile.save(
            update_fields=["onboarding_completed_at", "onboarding_version", "timezone_name"]
        )
        self.client.force_login(self.user)

    def _get_home(self):
        with patch(
            "notas.presentation.pages.home_calendarization.timezone.now",
            return_value=FIXED_NOW,
        ):
            return self.client.get(reverse("home_view"))

    def test_home_renders_empty_calendarization_and_current_monday_to_sunday(self):
        response = self._get_home()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Calendario")
        self.assertContains(response, "No tienes un programa calendarizado")
        calendarization = response.context["vm"]["content"]["calendarization"]
        self.assertEqual(len(calendarization["days"]), 7)
        self.assertEqual(calendarization["days"][0]["iso_date"], "2026-07-13")
        self.assertEqual(calendarization["days"][-1]["iso_date"], "2026-07-19")
        self.assertEqual([day["weekday_label"] for day in calendarization["days"]], list("LMMJVSD"))

    def test_home_shows_program_plan_and_link_for_selected_week(self):
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa Fuerza",
            start_date=date(2026, 7, 13),
            end_date=date(2026, 7, 19),
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        dailyplan = DailyPlan.objects.create(
            name="Plan de potencia",
            created_by=self.user,
            is_draft=False,
        )
        CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=date(2026, 7, 13),
            week_number=1,
            day_number=1,
            source_dailyplan_id=dailyplan.id,
            plan_snapshot={"name": "Plan de potencia"},
        )
        CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=date(2026, 7, 15),
            week_number=1,
            day_number=3,
            plan_snapshot=None,
        )

        response = self._get_home()

        self.assertContains(response, "Programa Fuerza")
        self.assertContains(response, "Plan de potencia")
        self.assertContains(response, 'class="card home-calendar__dailyplan-card"')
        calendarization_vm = response.context["vm"]["content"]["calendarization"]
        monday_vm = calendarization_vm["days"][0]
        today_vm = calendarization_vm["days"][2]
        sunday_vm = calendarization_vm["days"][6]
        self.assertEqual(monday_vm["temporal_state"], "past")
        self.assertTrue(monday_vm["has_plan"])
        self.assertEqual(today_vm["temporal_state"], "today")
        self.assertFalse(today_vm["has_plan"])
        self.assertEqual(sunday_vm["temporal_state"], "future")
