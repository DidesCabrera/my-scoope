from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class CalendarDayFoundationMigrationTests(TransactionTestCase):
    migrate_from = [("notas", "0072_food_visual_identity")]
    migrate_to = [("notas", "0076_calendar_day_origin")]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        old_apps = self.executor.loader.project_state(self.migrate_from).apps
        User = old_apps.get_model("auth", "User")
        Calendarization = old_apps.get_model("notas", "ProgramCalendarization")
        Day = old_apps.get_model("notas", "CalendarizedDay")
        Execution = old_apps.get_model("notas", "CalendarizedMealExecution")

        user = User.objects.create(username="calendar-migration-owner")
        date_with_overlap = date(2026, 7, 20)
        older = Calendarization.objects.create(
            user_id=user.id,
            program_name_snapshot="Programa con ejecución",
            start_date=date_with_overlap,
            end_date=date_with_overlap,
            status="cancelled",
        )
        newer = Calendarization.objects.create(
            user_id=user.id,
            program_name_snapshot="Programa sin ejecución",
            start_date=date_with_overlap,
            end_date=date_with_overlap,
            status="completed",
        )
        executed_day = Day.objects.create(
            calendarization_id=older.id,
            calendar_date=date_with_overlap,
            week_number=1,
            day_number=1,
            plan_snapshot={"name": "Plan realizado"},
        )
        later_day = Day.objects.create(
            calendarization_id=newer.id,
            calendar_date=date_with_overlap,
            week_number=1,
            day_number=1,
            plan_snapshot={"name": "Plan posterior"},
        )
        Execution.objects.create(
            calendarized_day_id=executed_day.id,
            meal_snapshot_key="meal-1",
            action="completed",
            idempotency_key="migration-executed-meal",
        )
        self.user_id = user.id
        self.executed_day_id = executed_day.id
        self.later_day_id = later_day.id

    def tearDown(self):
        MigrationExecutor(connection).migrate(self.migrate_to)
        super().tearDown()

    def test_backfill_preserves_executed_version_as_current(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        apps = self.executor.loader.project_state(self.migrate_to).apps
        Day = apps.get_model("notas", "CalendarizedDay")
        executed = Day.objects.get(pk=self.executed_day_id)
        later = Day.objects.get(pk=self.later_day_id)

        self.assertEqual(executed.user_id, self.user_id)
        self.assertEqual(executed.assignment_state, "current")
        self.assertEqual(executed.origin_calendarization_id, executed.calendarization_id)
        self.assertEqual(later.assignment_state, "superseded")
        self.assertEqual(later.change_reason, "legacy_date_overlap")
        self.assertEqual(later.plan_snapshot["name"], "Plan posterior")
