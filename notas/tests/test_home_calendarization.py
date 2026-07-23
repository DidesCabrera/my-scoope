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

    def _get_home(self, params=None):
        with patch(
            "notas.presentation.pages.home_calendarization.timezone.now",
            return_value=FIXED_NOW,
        ):
            return self.client.get(reverse("home_view"), data=params or {})

    def test_home_renders_empty_calendarization_and_current_monday_to_sunday(self):
        response = self._get_home()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Calendarización")
        self.assertContains(response, "Consulta tu programa calendarizado por semana")
        self.assertContains(response, "Mis Librerias")
        self.assertContains(response, "Resume tus programas, planes diarios, comidas y alimentos")
        self.assertContains(response, "Organiza estructuras semanales")
        self.assertContains(response, "Revisa tus planes diarios")
        self.assertContains(response, "home-stat-card__surface-link", count=4)
        self.assertNotContains(response, "Actualizar peso")
        self.assertNotContains(response, "home-footer")
        self.assertNotContains(response, "home-calendar__today-label")
        self.assertNotContains(response, "home-cta--icon")
        self.assertContains(response, "Herramientas")
        self.assertContains(response, "Accede al Comparador para revisar elementos lado a lado")
        self.assertContains(response, "Comparador")
        self.assertContains(response, "Explorador")
        self.assertContains(response, "Calendarizar")
        self.assertContains(response, reverse("comparator_index"))
        self.assertContains(response, reverse("food_comparator"))
        self.assertContains(response, reverse("calendarization_dashboard"))
        self.assertNotContains(response, 'type="button" aria-label="Semana anterior"')
        self.assertNotContains(response, 'type="button" aria-label="Semana siguiente"')
        self.assertContains(response, "No tienes un programa calendarizado")
        calendarization = response.context["vm"]["content"]["calendarization"]
        self.assertEqual(len(calendarization["days"]), 7)
        self.assertEqual(calendarization["days"][0]["iso_date"], "2026-07-13")
        self.assertEqual(calendarization["days"][-1]["iso_date"], "2026-07-19")
        self.assertEqual([day["weekday_label"] for day in calendarization["days"]], list("LMMJVSD"))
        self.assertEqual(calendarization["days"][2]["iso_date"], "2026-07-15")
        self.assertTrue(calendarization["days"][2]["is_selected"])
        self.assertEqual(len(calendarization["weeks"]), 1)
        self.assertFalse(calendarization["has_multiple_weeks"])

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
        self.assertContains(response, "Programa Calendarizado")
        self.assertContains(response, "Duración")
        self.assertContains(response, "7 días")
        self.assertContains(response, "3/7")
        self.assertContains(response, "Plan de potencia")
        self.assertContains(response, 'class="card home-calendar__dailyplan-card"')
        self.assertContains(response, "El programa calendarizado no tiene un plan asignado a esta fecha.")
        self.assertNotContains(response, "Sin plan diario")
        calendarization_vm = response.context["vm"]["content"]["calendarization"]
        self.assertEqual(calendarization_vm["end_label"], "19jul")
        self.assertEqual(calendarization_vm["progress_day"], 3)
        self.assertEqual(calendarization_vm["progress_total_days"], 7)
        self.assertEqual(calendarization_vm["progress_percent"], 43)
        self.assertEqual(len(calendarization_vm["weeks"]), 1)
        self.assertFalse(calendarization_vm["has_multiple_weeks"])
        self.assertNotContains(response, 'type="button" aria-label="Semana anterior"')
        self.assertNotContains(response, 'type="button" aria-label="Semana siguiente"')
        monday_vm = calendarization_vm["days"][0]
        today_vm = calendarization_vm["days"][2]
        sunday_vm = calendarization_vm["days"][6]
        self.assertEqual(monday_vm["temporal_state"], "past")
        self.assertTrue(monday_vm["has_plan"])
        self.assertEqual(today_vm["temporal_state"], "today")
        self.assertFalse(today_vm["has_plan"])
        self.assertEqual(sunday_vm["temporal_state"], "future")

    def test_home_clamps_unavailable_week_without_calendarization(self):
        response = self._get_home({"calendar_week": "2026-07-20"})

        self.assertEqual(response.status_code, 200)
        calendarization = response.context["vm"]["content"]["calendarization"]
        self.assertEqual(calendarization["days"][0]["iso_date"], "2026-07-13")
        self.assertEqual(calendarization["days"][-1]["iso_date"], "2026-07-19")
        self.assertTrue(calendarization["days"][2]["is_selected"])
        self.assertTrue(any(day["is_today"] for day in calendarization["days"]))

    def test_home_renders_only_calendarization_plan_weeks(self):
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa Extendido",
            start_date=date(2026, 7, 19),
            end_date=date(2026, 7, 27),
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        dailyplan = DailyPlan.objects.create(
            name="Plan frontera",
            created_by=self.user,
            is_draft=False,
        )
        CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=date(2026, 7, 19),
            week_number=1,
            day_number=1,
            source_dailyplan_id=dailyplan.id,
            plan_snapshot={"name": "Plan frontera"},
        )
        CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=date(2026, 7, 27),
            week_number=2,
            day_number=2,
            source_dailyplan_id=dailyplan.id,
            plan_snapshot={"name": "Plan frontera"},
        )

        response = self._get_home({"calendar_week": "2026-07-20", "calendar_date": "2026-07-27"})

        self.assertContains(response, 'type="button" aria-label="Semana anterior"')
        self.assertContains(response, 'type="button" aria-label="Semana siguiente"')
        self.assertContains(response, "data-home-calendar-day-link")
        calendarization_vm = response.context["vm"]["content"]["calendarization"]
        self.assertTrue(calendarization_vm["has_multiple_weeks"])
        self.assertEqual(
            [week["week_start_iso"] for week in calendarization_vm["weeks"]],
            ["2026-07-13", "2026-07-20", "2026-07-27"],
        )
        self.assertEqual(calendarization_vm["days"][0]["iso_date"], "2026-07-20")
        self.assertEqual(calendarization_vm["days"][-1]["iso_date"], "2026-07-26")
