from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from ai_assistant.application.objective_state import infer_active_work
from notas.application.ai_tools.prepared_actions import commit_prepared_action, prepare_workspace_patch
from notas.application.ai_tools.workspace_query_tools import query_workspace_tool
from notas.domain.models import CalendarCommitment, CalendarizedDay, DailyPlan, Program, ProgramCalendarization


class AICalendarAuthorityTests(TestCase):
    def setUp(self):
        model = get_user_model()
        self.user = model.objects.create_user(username="calendar-ai-owner")
        self.other = model.objects.create_user(username="calendar-ai-other")
        self.day = timezone.localdate() + timedelta(days=3)
        self.plan = DailyPlan.objects.create(name="Minuta propia", created_by=self.user)
        self.program = Program.objects.create(name="Plantilla", created_by=self.user)

    def _patch(self, resource, action, parameters, target_id=None):
        return prepare_workspace_patch(
            user=self.user, title="Calendario", summary="Cambio fechado", operations=[{
                "resource": resource, "action": action,
                "target_id": target_id, "parameters": parameters,
            }],
        )

    def test_calendar_read_covers_manual_day_and_commitment_without_program_projection(self):
        self.assertIsNone(self.program.start_date)
        action = self._patch("calendar_day", "assign_plan", {"date": self.day.isoformat(), "dailyplan_id": self.plan.id})
        self.assertFalse(CalendarizedDay.objects.filter(user=self.user).exists())
        commit_prepared_action(user=self.user, public_id=action.public_id)
        commitment = CalendarCommitment.objects.create(user=self.user, kind="training", calendar_date=self.day)
        read = query_workspace_tool(self.user, "calendar_day", date_from=self.day.isoformat())
        self.assertTrue(read.ok)
        self.assertEqual(read.data["item"]["source_kind"], "manual")
        self.assertEqual(read.data["item"]["commitments"][0]["id"], commitment.id)
        self.assertIsNone(query_workspace_tool(self.user, "program_projections").data["calendarization"]["current"])
        self.assertFalse(query_workspace_tool(self.other, "calendar_day", date_from=self.day.isoformat()).data["item"]["has_plan"])

    def test_commitments_are_confirmed_and_owner_scoped(self):
        action = self._patch("calendar_commitment", "create", {
            "kind": "training", "dates": [self.day.isoformat()], "note": "Fuerza",
        })
        self.assertFalse(CalendarCommitment.objects.filter(user=self.user).exists())
        commit_prepared_action(user=self.user, public_id=action.public_id)
        commitment = CalendarCommitment.objects.get(user=self.user)
        self.assertEqual(commitment.note, "Fuerza")
        with self.assertRaises(ValueError):
            prepare_workspace_patch(user=self.other, title="X", summary="X", operations=[{
                "resource": "calendar_commitment", "action": "delete", "target_id": commitment.id, "parameters": {},
            }])
        edited = self._patch("calendar_commitment", "update", {"note": "Piernas"}, commitment.id)
        commit_prepared_action(user=self.user, public_id=edited.public_id)
        commitment.refresh_from_db()
        self.assertEqual(commitment.note, "Piernas")

    def test_calendar_words_do_not_pause_a_program_projection(self):
        read = infer_active_work(None, current_user_message="Revisa mi calendario actual")
        self.assertEqual(read["resource"], "calendar")
        pause = infer_active_work(None, current_user_message="Pausa mi calendario")
        self.assertEqual(pause["expected_outcome"], "clarification_required")

    def test_projecting_program_dates_the_instance_not_the_template(self):
        action = self._patch("program_projection", "project", {
            "program_id": self.program.id, "start_date": self.day.isoformat(),
            "timezone_name": "UTC", "confirm_incomplete": True,
        })
        preview = action.preview["operations"][0]["after"]
        self.assertEqual(len(preview["empty_dates"]), 7)
        self.assertFalse(ProgramCalendarization.objects.filter(user=self.user).exists())
        commit_prepared_action(user=self.user, public_id=action.public_id)
        self.program.refresh_from_db()
        self.assertIsNone(self.program.start_date)
        self.assertEqual(ProgramCalendarization.objects.get(user=self.user).start_date, self.day)

    def test_assignment_collision_requires_replacement_and_keeps_history(self):
        first = self._patch("calendar_day", "assign_plan", {
            "date": self.day.isoformat(), "dailyplan_id": self.plan.id,
        })
        commit_prepared_action(user=self.user, public_id=first.public_id)
        second = self._patch("calendar_day", "assign_plan", {
            "date": self.day.isoformat(), "dailyplan_id": self.plan.id,
        })
        self.assertIsNotNone(second.preview["operations"][0]["after"]["existing_day"])
        with self.assertRaisesMessage(ValueError, "calendar_replacement_confirmation_required"):
            commit_prepared_action(user=self.user, public_id=second.public_id)
        replacement = self._patch("calendar_day", "assign_plan", {
            "date": self.day.isoformat(), "dailyplan_id": self.plan.id, "replace_existing": True,
        })
        commit_prepared_action(user=self.user, public_id=replacement.public_id)
        self.assertEqual(CalendarizedDay.objects.filter(user=self.user).count(), 2)
        self.assertEqual(CalendarizedDay.objects.filter(
            user=self.user, assignment_state=CalendarizedDay.STATE_CURRENT,
        ).count(), 1)

    def test_stale_commitment_edit_is_rejected_before_commit(self):
        row = CalendarCommitment.objects.create(user=self.user, kind="training", calendar_date=self.day)
        action = self._patch("calendar_commitment", "update", {"note": "A"}, row.id)
        self.assertEqual(action.preview["operations"][0]["after"]["note"], "A")
        row.note = "Cambio externo"
        row.save(update_fields=["note"])
        with self.assertRaisesMessage(ValueError, "prepared_action_target_changed"):
            commit_prepared_action(user=self.user, public_id=action.public_id)
        row.refresh_from_db()
        self.assertEqual(row.note, "Cambio externo")

    def test_projection_refuses_occupied_manual_date_and_rolls_back(self):
        assignment = self._patch("calendar_day", "assign_plan", {
            "date": self.day.isoformat(), "dailyplan_id": self.plan.id,
        })
        commit_prepared_action(user=self.user, public_id=assignment.public_id)
        projection = self._patch("program_projection", "project", {
            "program_id": self.program.id, "start_date": self.day.isoformat(),
            "timezone_name": "UTC", "confirm_incomplete": True,
        })
        self.assertEqual(projection.preview["operations"][0]["after"]["occupied_dates"], [self.day.isoformat()])
        with self.assertRaises(ValueError):
            commit_prepared_action(user=self.user, public_id=projection.public_id)
        self.assertFalse(ProgramCalendarization.objects.filter(user=self.user).exists())
        self.assertEqual(CalendarizedDay.objects.get(user=self.user).source_kind, "manual")
