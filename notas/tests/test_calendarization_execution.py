from datetime import timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from notas.application.queries.calendarization_execution_queries import (
    calendarization_measurement_summary,
    calendarization_progress_summary,
    meal_execution_state_for_day,
)
from notas.application.services.calendarization.snapshots import SNAPSHOT_SCHEMA_VERSION
from notas.application.services.commands.calendarization_execution_commands import (
    create_calendarization_review,
    decide_calendarization_revision,
    prepare_calendarization_revision,
    record_calendarized_weight,
    record_meal_execution,
)
from notas.domain.models import (
    CalendarizationMeasurementContext,
    CalendarizationRevision,
    CalendarizedDay,
    CalendarizedMealExecution,
    ProgramCalendarization,
)


def plan_snapshot(name="Plan original", meal_key="dailyplan_meal:1", kcal=2200):
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "name": name,
        "meals": [
            {
                "key": meal_key,
                "name": "Desayuno",
                "hour": "08:00",
                "foods": [],
                "totals": {"protein_g": 40, "carbs_g": 60, "fat_g": 15, "total_kcal": 535},
            }
        ],
        "totals": {"protein_g": 180, "carbs_g": 250, "fat_g": 55, "total_kcal": kcal},
    }


class CalendarizationExecutionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="lived-program-user")
        self.today = timezone.now().astimezone(ZoneInfo("UTC")).date()
        self.calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa vivido",
            start_date=self.today,
            end_date=self.today + timedelta(days=6),
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        self.day = CalendarizedDay.objects.create(
            calendarization=self.calendarization,
            calendar_date=self.today,
            week_number=1,
            day_number=1,
            plan_snapshot=plan_snapshot(),
            snapshot_hash="a" * 64,
        )

    def test_meal_corrections_append_evidence_instead_of_rewriting_it(self):
        first = record_meal_execution(
            user=self.user,
            day_id=self.day.id,
            meal_snapshot_key="dailyplan_meal:1",
            action="completed",
            idempotency_key="meal-event-0001",
        )
        same = record_meal_execution(
            user=self.user,
            day_id=self.day.id,
            meal_snapshot_key="dailyplan_meal:1",
            action="completed",
            idempotency_key="meal-event-0001",
        )
        record_meal_execution(
            user=self.user,
            day_id=self.day.id,
            meal_snapshot_key="dailyplan_meal:1",
            action="reset",
            idempotency_key="meal-event-0002",
        )

        self.assertEqual(first.id, same.id)
        self.assertEqual(CalendarizedMealExecution.objects.count(), 2)
        self.assertEqual(meal_execution_state_for_day(self.day)[0]["status"], "planned")

    def test_meal_evidence_requires_owned_today_snapshot_key(self):
        other = User.objects.create_user(username="other-calendar-user")

        with self.assertRaisesMessage(ValueError, "calendarized_day_not_found"):
            record_meal_execution(
                user=other,
                day_id=self.day.id,
                meal_snapshot_key="dailyplan_meal:1",
                action="completed",
                idempotency_key="meal-event-other",
            )
        with self.assertRaisesMessage(ValueError, "meal_snapshot_key_invalid"):
            record_meal_execution(
                user=self.user,
                day_id=self.day.id,
                meal_snapshot_key="invented",
                action="completed",
                idempotency_key="meal-event-invalid",
            )

    def test_weights_are_contextualized_without_moving_weight_ownership(self):
        weight, context = record_calendarized_weight(
            user=self.user,
            weight_kg=82.4,
            measured_on=self.today,
        )

        self.assertEqual(context.weight_log_id, weight.id)
        self.assertEqual(context.calendarization, self.calendarization)
        self.assertEqual(context.calendarized_day, self.day)
        self.assertEqual(CalendarizationMeasurementContext.objects.count(), 1)

    def test_review_freezes_adherence_and_measurement_summary(self):
        record_meal_execution(
            user=self.user,
            day_id=self.day.id,
            meal_snapshot_key="dailyplan_meal:1",
            action="completed",
            idempotency_key="meal-event-review",
        )
        record_calendarized_weight(user=self.user, weight_kg=82.4, measured_on=self.today)
        review = create_calendarization_review(
            user=self.user,
            period_start=self.today,
            period_end=self.today,
            energy_score=4,
            hunger_score=2,
            training_performance_score=5,
            note="Buen rendimiento.",
            idempotency_key="review-event-0001",
        )

        self.assertEqual(review.summary_snapshot["adherence"]["adherence_percent"], 100)
        self.assertEqual(review.summary_snapshot["measurements"]["latest_weight_kg"], 82.4)
        self.assertEqual(
            calendarization_progress_summary(
                self.calendarization,
                period_start=self.today,
                period_end=self.today,
            )["completed_meals"],
            1,
        )
        self.assertEqual(calendarization_measurement_summary(self.calendarization)["count"], 1)

    def test_approved_revision_changes_only_selected_future_snapshots(self):
        future_day = CalendarizedDay.objects.create(
            calendarization=self.calendarization,
            calendar_date=self.today + timedelta(days=1),
            week_number=1,
            day_number=2,
            plan_snapshot=plan_snapshot(),
            snapshot_hash="b" * 64,
        )
        replacement = plan_snapshot(name="Plan ajustado", meal_key="dailyplan_meal:2", kcal=2050)
        revision = prepare_calendarization_revision(
            user=self.user,
            calendarization_id=self.calendarization.id,
            effective_from=future_day.calendar_date,
            replacement_days=[
                {"calendar_date": future_day.calendar_date, "plan_snapshot": replacement},
            ],
            rationale="Ajuste prospectivo después de la revisión.",
            idempotency_key="revision-event-0001",
        )

        decide_calendarization_revision(
            user=self.user,
            revision_id=revision.id,
            decision="approve",
        )

        revision.refresh_from_db()
        future_day.refresh_from_db()
        self.day.refresh_from_db()
        self.assertEqual(revision.status, CalendarizationRevision.STATUS_APPLIED)
        self.assertEqual(future_day.plan_snapshot["name"], "Plan ajustado")
        self.assertEqual(self.day.plan_snapshot["name"], "Plan original")

    def test_revision_rejects_current_day_and_future_day_with_execution(self):
        with self.assertRaisesMessage(ValueError, "calendarization_revision_effective_date_invalid"):
            prepare_calendarization_revision(
                user=self.user,
                calendarization_id=self.calendarization.id,
                effective_from=self.today,
                replacement_days=[{"calendar_date": self.today, "plan_snapshot": plan_snapshot()}],
                rationale="No debe tocar hoy.",
                idempotency_key="revision-event-0002",
            )

        future_day = CalendarizedDay.objects.create(
            calendarization=self.calendarization,
            calendar_date=self.today + timedelta(days=1),
            week_number=1,
            day_number=2,
            plan_snapshot=plan_snapshot(meal_key="dailyplan_meal:future"),
        )
        CalendarizedMealExecution.objects.create(
            calendarized_day=future_day,
            meal_snapshot_key="dailyplan_meal:future",
            action=CalendarizedMealExecution.ACTION_COMPLETED,
            idempotency_key="future-evidence-0001",
        )
        with self.assertRaisesMessage(ValueError, "calendarization_revision_day_already_executed"):
            prepare_calendarization_revision(
                user=self.user,
                calendarization_id=self.calendarization.id,
                effective_from=future_day.calendar_date,
                replacement_days=[{"calendar_date": future_day.calendar_date, "plan_snapshot": plan_snapshot()}],
                rationale="No debe reescribir evidencia.",
                idempotency_key="revision-event-0003",
            )

    def test_revision_cannot_overwrite_a_future_day_changed_after_preparation(self):
        future_day = CalendarizedDay.objects.create(
            calendarization=self.calendarization,
            calendar_date=self.today + timedelta(days=1),
            week_number=1,
            day_number=2,
            plan_snapshot=plan_snapshot(),
            snapshot_hash="b" * 64,
        )
        revision = prepare_calendarization_revision(
            user=self.user,
            calendarization_id=self.calendarization.id,
            effective_from=future_day.calendar_date,
            replacement_days=[
                {
                    "calendar_date": future_day.calendar_date,
                    "plan_snapshot": plan_snapshot(name="Propuesta", meal_key="dailyplan_meal:2"),
                },
            ],
            rationale="Propuesta preparada sobre una versión conocida.",
            idempotency_key="revision-event-0004",
        )
        future_day.plan_snapshot = plan_snapshot(name="Cambio posterior", meal_key="dailyplan_meal:3")
        future_day.snapshot_hash = "c" * 64
        future_day.save(update_fields=["plan_snapshot", "snapshot_hash"])

        with self.assertRaisesMessage(ValueError, "calendarization_revision_no_longer_eligible"):
            decide_calendarization_revision(
                user=self.user,
                revision_id=revision.id,
                decision="approve",
            )
