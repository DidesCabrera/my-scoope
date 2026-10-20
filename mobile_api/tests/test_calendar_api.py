from datetime import timedelta

from django.test import override_settings

from mobile_api.selectors import local_date_for_user
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import (
    CalendarizedDay,
    CalendarizedMealExecution,
    CalendarProgressPeriod,
    DailyPlan,
    DailyPlanMeal,
    Meal,
    ProgramCalendarization,
)


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class CalendarAPITests(AuthenticatedMobileAPITestCase):
    def setUp(self):
        super().setUp()
        self.plan = DailyPlan.objects.create(name="Plan inicial", created_by=self.user)
        self.meal = Meal.objects.create(name="Comida inicial", created_by=self.user)
        self.meal_relation = DailyPlanMeal.objects.create(dailyplan=self.plan, meal=self.meal)
        self.today = local_date_for_user(self.user)

    def test_assigning_a_date_materializes_snapshot_and_today_reads_it(self):
        response = self.client.put(
            f"/api/v1/calendar/days/{self.today}/plan",
            data={"dailyplan_id": self.plan.id, "assignment_key": "calendar-assignment-0001"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        day_id = response.json()["data"]["id"]
        self.plan.name = "Nombre posterior"
        self.plan.save(update_fields=["name"])

        today = self.client.get("/api/v1/today").json()["data"]
        self.assertEqual(today["day_id"], day_id)
        self.assertEqual(today["plan_snapshot"]["name"], "Plan inicial")
        self.assertIsNone(today["calendarization"])
        self.assertIsNone(today["pinned_plan"])
        detail = self.client.get(f"/api/v1/program/days/{day_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["data"]["plan_name"], "Plan inicial")

        check_in = self.client.post(
            f"/api/v1/days/{day_id}/meals/dailyplan_meal:{self.meal_relation.id}/check-ins",
            data={"action": "completed", "idempotency_key": "calendar-check-in-0001"},
            content_type="application/json",
        )
        self.assertEqual(check_in.status_code, 200)
        self.assertEqual(check_in.json()["data"]["meal_execution"][0]["status"], "completed")

    def test_create_draft_for_today_creates_one_dated_snapshot_idempotently(self):
        payload = {"assignment_key": "calendar-draft-0001"}
        first = self.client.post(
            f"/api/v1/calendar/days/{self.today}/plan/draft",
            data=payload, content_type="application/json",
        )
        second = self.client.post(
            f"/api/v1/calendar/days/{self.today}/plan/draft",
            data=payload, content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["data"]["id"], second.json()["data"]["id"])
        self.assertEqual(CalendarizedDay.objects.filter(user=self.user).count(), 1)
        self.assertEqual(DailyPlan.objects.filter(created_by=self.user).count(), 2)
        today = self.client.get("/api/v1/today").json()["data"]
        self.assertEqual(today["day_id"], first.json()["data"]["id"])
        self.assertIsNone(today["pinned_plan"])

    def test_today_keeps_executed_day_visible_after_program_cancellation(self):
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa previo",
            start_date=self.today,
            end_date=self.today,
            status=ProgramCalendarization.STATUS_CANCELLED,
        )
        day = CalendarizedDay.objects.create(
            calendarization=calendarization,
            user=self.user,
            calendar_date=self.today,
            week_number=1,
            day_number=1,
            plan_snapshot={"name": "Día conservado", "meals": [{"key": "meal-1", "hour": "08:00"}]},
        )
        CalendarizedMealExecution.objects.create(
            calendarized_day=day,
            meal_snapshot_key="meal-1",
            action="completed",
            idempotency_key="cancelled-today-check-in",
        )
        response = self.client.get("/api/v1/today")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["day_id"], day.id)
        self.assertEqual(response.json()["data"]["plan_snapshot"]["name"], "Día conservado")

    def test_manual_date_overrides_program_day_in_today_and_active_projection(self):
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa anterior",
            start_date=self.today,
            end_date=self.today,
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        original = CalendarizedDay.objects.create(
            calendarization=calendarization,
            origin_calendarization=calendarization,
            user=self.user,
            calendar_date=self.today,
            week_number=1,
            day_number=1,
            plan_snapshot={"name": "Plan del programa", "meals": []},
        )
        assigned = self.client.put(
            f"/api/v1/calendar/days/{self.today}/plan",
            data={"dailyplan_id": self.plan.id, "assignment_key": "manual-program-override-0001", "replace_existing": True},
            content_type="application/json",
        )
        self.assertEqual(assigned.status_code, 200)
        today = self.client.get("/api/v1/today").json()["data"]
        self.assertEqual(today["day_id"], assigned.json()["data"]["id"])
        self.assertEqual(today["plan_snapshot"]["name"], "Plan inicial")
        home = self.client.get("/api/v1/home").json()["data"]
        self.assertEqual(home["today"]["day_id"], today["day_id"])
        self.assertEqual(home["active_program"]["days"], [])
        original.refresh_from_db()
        self.assertEqual(original.assignment_state, CalendarizedDay.STATE_SUPERSEDED)

    def test_overview_shows_four_weeks_and_replacement_requires_confirmation(self):
        future = self.today + timedelta(days=2)
        first = self.client.put(
            f"/api/v1/calendar/days/{future}/plan",
            data={"dailyplan_id": self.plan.id, "assignment_key": "calendar-assignment-0001"},
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)
        other = DailyPlan.objects.create(name="Plan sustituto", created_by=self.user)
        request_data = {"dailyplan_id": other.id, "assignment_key": "calendar-assignment-0002"}
        conflict = self.client.put(f"/api/v1/calendar/days/{future}/plan", data=request_data, content_type="application/json")
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["error"]["code"], "calendar_replacement_confirmation_required")
        request_data["replace_existing"] = True
        replaced = self.client.put(f"/api/v1/calendar/days/{future}/plan", data=request_data, content_type="application/json")
        self.assertEqual(replaced.status_code, 200)
        old = CalendarizedDay.objects.get(id=first.json()["data"]["id"])
        self.assertEqual(old.assignment_state, CalendarizedDay.STATE_SUPERSEDED)
        self.assertEqual(old.superseded_by_id, replaced.json()["data"]["id"])

        history = self.client.get(f"/api/v1/calendar/days/{future}/history")
        self.assertEqual(history.status_code, 200)
        versions = history.json()["data"]["items"]
        self.assertEqual([item["plan_name"] for item in versions], ["Plan inicial", "Plan sustituto"])
        self.assertEqual([item["assignment_state"] for item in versions], ["superseded", "current"])

        overview = self.client.get("/api/v1/calendar").json()["data"]
        self.assertEqual(len(overview["days"]), 28)
        by_date = {day["calendar_date"]: day for day in overview["days"]}
        self.assertEqual(by_date[future.isoformat()]["plan_name"], "Plan sustituto")

    def test_new_progress_period_resets_visible_metric_without_erasing_evidence(self):
        yesterday = self.today - timedelta(days=1)
        previous = CalendarizedDay.objects.create(
            user=self.user,
            calendar_date=yesterday,
            source_kind=CalendarizedDay.SOURCE_MANUAL,
            plan_snapshot={"name": "Plan anterior", "meals": [{"key": "old-meal", "hour": "08:00"}]},
        )
        CalendarizedMealExecution.objects.create(
            calendarized_day=previous,
            meal_snapshot_key="old-meal",
            action="skipped",
            idempotency_key="old-meal-skipped-0001",
        )
        current = self.client.put(
            f"/api/v1/calendar/days/{self.today}/plan",
            data={"dailyplan_id": self.plan.id, "assignment_key": "calendar-assignment-0001"},
            content_type="application/json",
        ).json()["data"]
        check_in = self.client.post(
            f"/api/v1/days/{current['id']}/meals/dailyplan_meal:{self.meal_relation.id}/check-ins",
            data={"action": "completed", "idempotency_key": "calendar-check-in-0001"},
            content_type="application/json",
        )
        self.assertEqual(check_in.status_code, 200)
        before = self.client.get("/api/v1/calendar/progress").json()["data"]
        self.assertEqual(before["adherence_percent"], 50)

        reset = self.client.post("/api/v1/calendar/progress/periods", data={}, content_type="application/json")
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.json()["data"]["adherence_percent"], 100)
        self.assertEqual(reset.json()["data"]["period_start"], self.today.isoformat())
        periods = list(CalendarProgressPeriod.objects.filter(user=self.user).order_by("starts_on"))
        self.assertEqual(len(periods), 2)
        self.assertEqual(periods[0].ends_on, yesterday)
        self.assertEqual(CalendarizedMealExecution.objects.filter(calendarized_day=previous).count(), 1)

    def test_move_manual_plan_keeps_original_snapshot(self):
        source_date = self.today + timedelta(days=1)
        target_date = self.today + timedelta(days=3)
        assigned = self.client.put(
            f"/api/v1/calendar/days/{source_date}/plan",
            data={"dailyplan_id": self.plan.id, "assignment_key": "calendar-assignment-0001"},
            content_type="application/json",
        )
        moved = self.client.post(
            f"/api/v1/calendar/days/{source_date}/move",
            data={"target_date": target_date.isoformat(), "assignment_key": "calendar-move-0001"},
            content_type="application/json",
        )
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(moved.status_code, 200)
        old = CalendarizedDay.objects.get(pk=assigned.json()["data"]["id"])
        self.assertEqual(old.superseded_by_id, moved.json()["data"]["id"])
        overview = self.client.get("/api/v1/calendar").json()["data"]
        by_date = {day["calendar_date"]: day for day in overview["days"]}
        self.assertFalse(by_date[source_date.isoformat()]["has_plan"])
        self.assertTrue(by_date[target_date.isoformat()]["has_plan"])
