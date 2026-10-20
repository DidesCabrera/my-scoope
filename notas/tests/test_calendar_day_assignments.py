from datetime import timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from notas.application.services.calendarization.scheduling import local_date_for_timezone
from notas.application.services.commands.calendar_day_commands import (
    assign_dailyplan_to_calendar_date,
    move_calendar_date_plan,
    remove_calendar_date_plan,
)
from notas.application.services.commands.calendarization_execution_commands import record_meal_execution
from notas.domain.models import CalendarizedDay, DailyPlan, DailyPlanMeal, Meal, PinnedDailyPlan


class CalendarDayAssignmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="calendar-day-owner", password="pw")
        self.other = User.objects.create_user(username="calendar-day-other", password="pw")
        self.user.profile.timezone_name = "UTC"
        self.user.profile.save(update_fields=["timezone_name"])
        self.plan = DailyPlan.objects.create(name="Plan de biblioteca", created_by=self.user)
        self.meal = Meal.objects.create(name="Desayuno", created_by=self.user)
        self.meal_relation = DailyPlanMeal.objects.create(dailyplan=self.plan, meal=self.meal)
        self.today = local_date_for_timezone("UTC")

    def assign(self, *, local_date=None, plan=None, key="assignment-0001", replace=False):
        return assign_dailyplan_to_calendar_date(
            user=self.user,
            dailyplan_id=(plan or self.plan).id,
            local_date=local_date or self.today,
            assignment_key=key,
            replace_existing=replace,
        )

    def test_assignment_is_a_snapshot_and_same_plan_can_appear_on_two_dates(self):
        first = self.assign()
        second = self.assign(local_date=self.today + timedelta(days=2), key="assignment-0002")
        self.plan.name = "Nombre cambiado en biblioteca"
        self.plan.save(update_fields=["name"])

        first.refresh_from_db()
        self.assertEqual(first.plan_snapshot["name"], "Plan de biblioteca")
        self.assertEqual(second.plan_snapshot["name"], "Plan de biblioteca")
        self.assertEqual(first.source_dailyplan_id, second.source_dailyplan_id)
        self.assertEqual(first.source_kind, CalendarizedDay.SOURCE_MANUAL)
        self.assertIsNone(first.calendarization_id)

    def test_today_assignment_retires_legacy_pin_without_deleting_its_evidence(self):
        pin = PinnedDailyPlan.objects.create(user=self.user, dailyplan=self.plan)
        self.assign()
        pin.refresh_from_db()
        self.assertFalse(pin.is_active)
        remove_calendar_date_plan(user=self.user, local_date=self.today)
        self.assertFalse(PinnedDailyPlan.objects.get(pk=pin.pk).is_active)

    def test_replacement_keeps_old_snapshot_and_links_new_assignment(self):
        day = self.today + timedelta(days=1)
        first = self.assign(local_date=day)
        replacement = DailyPlan.objects.create(name="Plan nuevo", created_by=self.user)
        with self.assertRaisesMessage(ValueError, "calendar_replacement_confirmation_required"):
            self.assign(local_date=day, plan=replacement, key="assignment-0002")

        second = self.assign(local_date=day, plan=replacement, key="assignment-0002", replace=True)
        first.refresh_from_db()
        self.assertEqual(first.assignment_state, CalendarizedDay.STATE_SUPERSEDED)
        self.assertEqual(first.plan_snapshot["name"], "Plan de biblioteca")
        self.assertEqual(first.superseded_by, second)
        self.assertEqual(second.plan_snapshot["name"], "Plan nuevo")
        self.assertEqual(self.assign(local_date=day, plan=replacement, key="assignment-0002", replace=True), second)

    def test_today_with_execution_cannot_be_replaced_or_removed(self):
        first = self.assign()
        record_meal_execution(
            user=self.user,
            day_id=first.id,
            meal_snapshot_key=f"dailyplan_meal:{self.meal_relation.id}",
            action="completed",
            idempotency_key="meal-check-0001",
        )
        replacement = DailyPlan.objects.create(name="Plan nuevo", created_by=self.user)
        with self.assertRaisesMessage(ValueError, "calendar_day_has_execution"):
            self.assign(plan=replacement, key="assignment-0002", replace=True)
        with self.assertRaisesMessage(ValueError, "calendar_day_has_execution"):
            remove_calendar_date_plan(user=self.user, local_date=self.today)
        first.refresh_from_db()
        self.assertEqual(first.assignment_state, CalendarizedDay.STATE_CURRENT)

    def test_removed_assignment_stays_in_history_and_date_can_be_reused(self):
        future = self.today + timedelta(days=1)
        first = self.assign(local_date=future)
        remove_calendar_date_plan(user=self.user, local_date=future)
        first.refresh_from_db()
        self.assertEqual(first.assignment_state, CalendarizedDay.STATE_REMOVED)
        self.assertEqual(self.assign(local_date=future, key="assignment-0002").assignment_state, CalendarizedDay.STATE_CURRENT)

    def test_move_preserves_source_snapshot_and_replaced_target(self):
        source_date = self.today + timedelta(days=1)
        target_date = self.today + timedelta(days=2)
        source = self.assign(local_date=source_date)
        target_plan = DailyPlan.objects.create(name="Plan del destino", created_by=self.user)
        target = self.assign(local_date=target_date, plan=target_plan, key="assignment-0002")
        with self.assertRaisesMessage(ValueError, "calendar_replacement_confirmation_required"):
            move_calendar_date_plan(
                user=self.user, source_date=source_date, target_date=target_date,
                assignment_key="assignment-0003",
            )

        moved = move_calendar_date_plan(
            user=self.user, source_date=source_date, target_date=target_date,
            assignment_key="assignment-0003", replace_existing=True,
        )
        source.refresh_from_db()
        target.refresh_from_db()
        self.assertEqual(source.assignment_state, CalendarizedDay.STATE_SUPERSEDED)
        self.assertEqual(source.superseded_by, moved)
        self.assertEqual(target.assignment_state, CalendarizedDay.STATE_SUPERSEDED)
        self.assertEqual(target.superseded_by, moved)
        self.assertEqual(target.plan_snapshot["name"], "Plan del destino")
        self.assertEqual(moved.plan_snapshot, source.plan_snapshot)
        self.assertEqual(
            move_calendar_date_plan(
                user=self.user, source_date=source_date, target_date=target_date,
                assignment_key="assignment-0003", replace_existing=True,
            ), moved,
        )

    def test_database_rejects_two_current_assignments_for_same_date(self):
        self.assign()
        with self.assertRaises(IntegrityError), transaction.atomic():
            CalendarizedDay.objects.create(
                user=self.user,
                calendar_date=self.today,
                source_kind=CalendarizedDay.SOURCE_MANUAL,
                assignment_state=CalendarizedDay.STATE_CURRENT,
                plan_snapshot={"name": "Otra"},
            )

    def test_cannot_assign_someone_elses_plan_or_a_past_date(self):
        with self.assertRaisesMessage(ValueError, "calendar_dailyplan_not_owned"):
            assign_dailyplan_to_calendar_date(
                user=self.other,
                dailyplan_id=self.plan.id,
                local_date=self.today,
                assignment_key="assignment-0002",
            )
        with self.assertRaisesMessage(ValueError, "calendar_date_in_past"):
            self.assign(local_date=self.today - timedelta(days=1))
