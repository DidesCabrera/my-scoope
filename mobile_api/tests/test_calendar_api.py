from datetime import timedelta

from django.contrib.auth.models import User
from django.test import override_settings

from mobile_api.selectors import local_date_for_user
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import (
    CalendarCommitment,
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

    def test_register_commitments_on_multiple_dates_and_show_them_alongside_plans(self):
        tomorrow = self.today + timedelta(days=1)
        CalendarizedDay.objects.create(
            user=self.user,
            calendar_date=self.today,
            source_kind=CalendarizedDay.SOURCE_MANUAL,
            plan_snapshot={"name": "Plan de hoy", "meals": []},
        )
        response = self.client.post(
            "/api/v1/calendar/commitments",
            data={"kind": "shopping", "dates": [self.today.isoformat(), tomorrow.isoformat()], "note": "Comprar verduras"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]["items"]), 2)
        self.assertEqual(CalendarCommitment.objects.filter(user=self.user).count(), 2)

        cooking = self.client.post(
            "/api/v1/calendar/commitments",
            data={"kind": "cooking", "dates": [self.today.isoformat()], "note": "Preparar almuerzo"},
            content_type="application/json",
        )
        self.assertEqual(cooking.status_code, 200)
        overview = self.client.get("/api/v1/calendar").json()["data"]
        days = {item["calendar_date"]: item for item in overview["days"]}
        self.assertTrue(days[self.today.isoformat()]["has_plan"])
        self.assertEqual({item["kind"] for item in days[self.today.isoformat()]["commitments"]}, {"shopping", "cooking"})
        self.assertFalse(days[tomorrow.isoformat()]["has_plan"])
        self.assertEqual(days[tomorrow.isoformat()]["commitments"][0]["note"], "Comprar verduras")
        day_without_plan = self.client.get(f"/api/v1/calendar/days/{tomorrow}").json()["data"]
        self.assertEqual(day_without_plan["commitments"][0]["kind"], "shopping")

    def test_commitment_batch_rejects_duplicates_and_past_dates_without_partial_write(self):
        tomorrow = self.today + timedelta(days=1)
        later = self.today + timedelta(days=2)
        CalendarCommitment.objects.create(user=self.user, calendar_date=tomorrow, kind="training", note="Original")
        conflict = self.client.post(
            "/api/v1/calendar/commitments",
            data={"kind": "training", "dates": [tomorrow.isoformat(), later.isoformat()], "note": "Nuevo"},
            content_type="application/json",
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertFalse(CalendarCommitment.objects.filter(user=self.user, calendar_date=later).exists())
        self.assertEqual(CalendarCommitment.objects.get(user=self.user, calendar_date=tomorrow).note, "Original")

        past = self.client.post(
            "/api/v1/calendar/commitments",
            data={"kind": "shopping", "dates": [(self.today - timedelta(days=1)).isoformat(), later.isoformat()]},
            content_type="application/json",
        )
        self.assertEqual(past.status_code, 422)
        self.assertFalse(CalendarCommitment.objects.filter(user=self.user, calendar_date=later).exists())

    def test_calendar_foods_sum_current_snapshots_in_inclusive_period(self):
        def snapshot(quantity):
            return {
                "name": "Plan guardado",
                "totals": {"total_kcal": 100, "protein_g": 10, "carbs_g": 10, "fat_g": 2},
                "meals": [{"foods": [{
                    "name": "Avena", "quantity_g": quantity, "quantity_unit": "g",
                    "protein_g": 5, "carbs_g": 8, "fat_g": 1, "total_kcal": 61,
                }]}],
            }

        tomorrow = self.today + timedelta(days=1)
        CalendarizedDay.objects.create(user=self.user, calendar_date=self.today,
            source_kind=CalendarizedDay.SOURCE_MANUAL, plan_snapshot=snapshot(70))
        CalendarizedDay.objects.create(user=self.user, calendar_date=tomorrow,
            source_kind=CalendarizedDay.SOURCE_MANUAL, plan_snapshot=snapshot(80))
        CalendarizedDay.objects.create(user=self.user, calendar_date=tomorrow,
            source_kind=CalendarizedDay.SOURCE_MANUAL,
            assignment_state=CalendarizedDay.STATE_SUPERSEDED, plan_snapshot=snapshot(900))
        CalendarizedDay.objects.create(user=User.objects.create_user(username="other-foods"),
            calendar_date=self.today, source_kind=CalendarizedDay.SOURCE_MANUAL, plan_snapshot=snapshot(400))
        program_date = tomorrow + timedelta(days=1)
        calendarization = ProgramCalendarization.objects.create(
            user=self.user, program_name_snapshot="Programa previo",
            start_date=self.today, end_date=program_date,
        )
        CalendarizedDay.objects.create(calendarization=calendarization, calendar_date=program_date,
            source_kind=CalendarizedDay.SOURCE_PROGRAM, week_number=1, day_number=3,
            plan_snapshot=snapshot(50))
        CalendarizedDay.objects.create(user=self.user, calendar_date=program_date + timedelta(days=1),
            source_kind=CalendarizedDay.SOURCE_MANUAL, plan_snapshot=snapshot(500))

        response = self.client.get("/api/v1/calendar/foods", {
            "start_date": self.today.isoformat(), "end_date": program_date.isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        result = response.json()["data"]
        self.assertEqual(result["plans_count"], 3)
        self.assertEqual(len(result["foods"]), 1)
        self.assertEqual(result["foods"][0]["name"], "Avena")
        self.assertEqual(result["foods"][0]["quantity"], 200)
        self.assertEqual(result["foods"][0]["quantity_unit"], "g")

    def test_calendar_foods_validates_period_and_handles_empty_dates(self):
        empty = self.client.get("/api/v1/calendar/foods", {
            "start_date": self.today.isoformat(), "end_date": self.today.isoformat(),
        })
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json()["data"]["foods"], [])
        reversed_period = self.client.get("/api/v1/calendar/foods", {
            "start_date": (self.today + timedelta(days=1)).isoformat(), "end_date": self.today.isoformat(),
        })
        self.assertEqual(reversed_period.status_code, 422)
        too_long = self.client.get("/api/v1/calendar/foods", {
            "start_date": self.today.isoformat(),
            "end_date": (self.today + timedelta(days=366)).isoformat(),
        })
        self.assertEqual(too_long.status_code, 422)

    def test_shopping_commitment_saves_food_period_and_immutable_list_for_each_date(self):
        tomorrow = self.today + timedelta(days=1)
        snapshot = {
            "name": "Plan para compras",
            "totals": {"total_kcal": 124, "protein_g": 1, "carbs_g": 30, "fat_g": 0},
            "meals": [{"foods": [{
                "name": "Plátano", "quantity_g": 140, "quantity_unit": "g",
                "protein_g": 1, "carbs_g": 30, "fat_g": 0, "total_kcal": 124,
            }]}],
        }
        day = CalendarizedDay.objects.create(
            user=self.user, calendar_date=tomorrow,
            source_kind=CalendarizedDay.SOURCE_MANUAL, plan_snapshot=snapshot,
        )
        payload = {
            "kind": "shopping", "dates": [self.today.isoformat(), tomorrow.isoformat()],
            "food_period_start": tomorrow.isoformat(), "food_period_end": tomorrow.isoformat(),
        }
        response = self.client.post("/api/v1/calendar/commitments", data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]["items"]
        self.assertEqual([item["food_plans_count"] for item in items], [1, 1])
        self.assertEqual([item["foods"][0]["quantity"] for item in items], [140, 140])
        self.assertEqual(items[0]["food_period_start"], tomorrow.isoformat())
        self.assertEqual(items[0]["food_period_end"], tomorrow.isoformat())

        day.plan_snapshot = {"name": "Plan modificado", "meals": []}
        day.save(update_fields=["plan_snapshot"])
        saved = CalendarCommitment.objects.get(user=self.user, calendar_date=self.today, kind="shopping")
        self.assertEqual(saved.foods_snapshot[0]["rel"]["quantity"], 140)
        detail = self.client.get(f"/api/v1/calendar/days/{self.today}").json()["data"]
        self.assertEqual(detail["commitments"][0]["foods"][0]["quantity"], 140)
        overview = self.client.get("/api/v1/calendar").json()["data"]
        selected = next(item for item in overview["days"] if item["calendar_date"] == self.today.isoformat())
        self.assertEqual(selected["commitments"][0]["foods"][0]["name"], "Plátano")

    def test_shopping_period_must_be_a_valid_pair_and_other_kinds_cannot_use_it(self):
        tomorrow = self.today + timedelta(days=1)
        for kind, start, end in (
            ("shopping", tomorrow, None),
            ("shopping", tomorrow, self.today),
            ("cooking", self.today, self.today),
        ):
            response = self.client.post("/api/v1/calendar/commitments", data={
                "kind": kind, "dates": [self.today.isoformat()],
                "food_period_start": start.isoformat(),
                "food_period_end": end.isoformat() if end else None,
            }, content_type="application/json")
            self.assertEqual(response.status_code, 422)
        self.assertFalse(CalendarCommitment.objects.filter(user=self.user).exists())

    def test_overview_summarizes_all_future_current_plans_beyond_visible_month(self):
        empty = self.client.get("/api/v1/calendar").json()["data"]
        self.assertEqual(empty["future_plans_count"], 0)
        self.assertIsNone(empty["last_scheduled_date"])

        last_date = self.today + timedelta(days=90)
        for offset, state, snapshot in (
            (-1, CalendarizedDay.STATE_CURRENT, {"name": "Pasado"}),
            (0, CalendarizedDay.STATE_CURRENT, {"name": "Hoy"}),
            (10, CalendarizedDay.STATE_CURRENT, {}),
            (30, CalendarizedDay.STATE_SUPERSEDED, {"name": "Sustituido"}),
            (90, CalendarizedDay.STATE_CURRENT, {"name": "Último"}),
        ):
            CalendarizedDay.objects.create(
                user=self.user,
                calendar_date=self.today + timedelta(days=offset),
                source_kind=CalendarizedDay.SOURCE_MANUAL,
                assignment_state=state,
                plan_snapshot=snapshot,
            )

        response = self.client.get("/api/v1/calendar", {"start_date": self.today.isoformat(), "days": 7})
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["future_plans_count"], 2)
        self.assertEqual(data["last_scheduled_date"], last_date.isoformat())

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
        self.assertEqual(before["scheduled_meals"], 2)
        self.assertEqual(before["days_with_plan"], 2)
        self.assertEqual(before["completed_meals"], 1)
        self.assertEqual(before["elapsed_meals"], 2)

        reset = self.client.post("/api/v1/calendar/progress/periods", data={}, content_type="application/json")
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.json()["data"]["adherence_percent"], 100)
        self.assertEqual(reset.json()["data"]["period_start"], self.today.isoformat())
        self.assertEqual(reset.json()["data"]["scheduled_meals"], 1)
        self.assertEqual(reset.json()["data"]["days_with_plan"], 1)
        self.assertEqual(reset.json()["data"]["completed_meals"], 1)
        self.assertEqual(reset.json()["data"]["elapsed_meals"], 1)
        periods = list(CalendarProgressPeriod.objects.filter(user=self.user).order_by("starts_on"))
        self.assertEqual(len(periods), 2)
        self.assertEqual(periods[0].ends_on, yesterday)
        self.assertEqual(CalendarizedMealExecution.objects.filter(calendarized_day=previous).count(), 1)

    def test_progress_does_not_count_calendar_days_without_a_plan(self):
        CalendarizedDay.objects.create(
            user=self.user,
            calendar_date=self.today,
            source_kind=CalendarizedDay.SOURCE_MANUAL,
            plan_snapshot={},
        )
        progress = self.client.get("/api/v1/calendar/progress").json()["data"]
        self.assertEqual(progress["scheduled_meals"], 0)
        self.assertEqual(progress["days_with_plan"], 0)
        self.assertEqual(progress["elapsed_meals"], 0)

    def test_progress_totals_include_future_plans_and_meals_in_current_period(self):
        tomorrow = self.today + timedelta(days=1)
        CalendarProgressPeriod.objects.create(user=self.user, starts_on=self.today)
        CalendarizedDay.objects.create(
            user=self.user,
            calendar_date=self.today,
            source_kind=CalendarizedDay.SOURCE_MANUAL,
            plan_snapshot={"name": "Hoy", "meals": [{"key": "breakfast", "hour": "08:00"}]},
        )
        CalendarizedDay.objects.create(
            user=self.user,
            calendar_date=tomorrow,
            source_kind=CalendarizedDay.SOURCE_MANUAL,
            plan_snapshot={"name": "Mañana", "meals": [{"key": "lunch", "hour": "13:00"}, {"key": "dinner", "hour": "20:00"}]},
        )

        progress = self.client.get("/api/v1/calendar/progress").json()["data"]
        self.assertEqual(progress["days_with_plan"], 1)
        self.assertEqual(progress["scheduled_meals"], 3)
        self.assertEqual(progress["elapsed_meals"], 1)

    def test_adjust_progress_start_recalculates_range_and_keeps_prior_period(self):
        yesterday = self.today - timedelta(days=1)
        CalendarizedDay.objects.create(
            user=self.user,
            calendar_date=yesterday,
            source_kind=CalendarizedDay.SOURCE_MANUAL,
            plan_snapshot={"name": "Ayer", "meals": [{"key": "old-meal", "hour": "08:00"}]},
        )
        CalendarizedDay.objects.create(
            user=self.user,
            calendar_date=self.today,
            source_kind=CalendarizedDay.SOURCE_MANUAL,
            plan_snapshot={"name": "Hoy", "meals": [{"key": "new-meal", "hour": "08:00"}]},
        )
        previous_period = CalendarProgressPeriod.objects.create(user=self.user, starts_on=self.today)

        response = self.client.put(
            "/api/v1/calendar/progress/periods/current",
            data={"start_date": yesterday.isoformat()},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["period_start"], yesterday.isoformat())
        self.assertEqual(response.json()["data"]["days_with_plan"], 2)
        self.assertEqual(response.json()["data"]["scheduled_meals"], 2)
        previous_period.refresh_from_db()
        self.assertIsNotNone(previous_period.closed_at)
        self.assertEqual(CalendarProgressPeriod.objects.filter(user=self.user).count(), 2)

        repeated = self.client.put(
            "/api/v1/calendar/progress/periods/current",
            data={"start_date": yesterday.isoformat()},
            content_type="application/json",
        )
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(CalendarProgressPeriod.objects.filter(user=self.user).count(), 2)

        narrower = self.client.put(
            "/api/v1/calendar/progress/periods/current",
            data={"start_date": self.today.isoformat()},
            content_type="application/json",
        )
        self.assertEqual(narrower.status_code, 200)
        self.assertEqual(narrower.json()["data"]["days_with_plan"], 1)
        self.assertEqual(narrower.json()["data"]["scheduled_meals"], 1)
        self.assertEqual(CalendarProgressPeriod.objects.filter(user=self.user).count(), 3)

    def test_adjust_progress_start_rejects_future_date_without_changing_period(self):
        current = CalendarProgressPeriod.objects.create(user=self.user, starts_on=self.today)
        response = self.client.put(
            "/api/v1/calendar/progress/periods/current",
            data={"start_date": (self.today + timedelta(days=1)).isoformat()},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 422)
        current.refresh_from_db()
        self.assertIsNone(current.ends_on)
        self.assertEqual(CalendarProgressPeriod.objects.filter(user=self.user).count(), 1)

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
