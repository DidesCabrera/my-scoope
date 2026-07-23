from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from ai_assistant.application.tools import (
    TOOL_LIST_INBOX_ITEMS,
    TOOL_LIST_USER_PROGRAMS,
    TOOL_READ_ACCOUNT_BILLING_CONTEXT,
    TOOL_READ_CALENDARIZATION,
    TOOL_READ_PROGRAM,
    execute_read_only_tool,
)
from ai_assistant.domain import AssistantToolRequest, AssistantToolStatus
from notas.domain.models import (
    DailyPlan,
    DailyPlanShare,
    Program,
    ProgramCalendarization,
    ProgramDay,
)


class AssistantWorkspaceReadToolTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="pass123",
        )
        self.sender = User.objects.create_user(
            username="sender",
            email="sender@example.com",
            password="pass123",
        )
        self.dailyplan = DailyPlan.objects.create(
            name="Plan del programa",
            created_by=self.user,
            is_draft=False,
        )
        self.program = Program.objects.create(
            name="Programa fuerza",
            created_by=self.user,
            duration_weeks=2,
            is_draft=False,
        )
        ProgramDay.objects.create(
            program=self.program,
            dailyplan=self.dailyplan,
            week_number=1,
            day_number=1,
        )
        self.calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            source_program=self.program,
            program_name_snapshot=self.program.name,
            start_date=date(2026, 7, 20),
            end_date=date(2026, 8, 2),
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        DailyPlanShare.objects.create(
            sender=self.sender,
            recipient_email=self.user.email,
            dailyplan=self.dailyplan,
            accepted_by=self.user,
            subject="Plan compartido",
        )
    def execute(self, tool_name, arguments=None):
        return execute_read_only_tool(
            AssistantToolRequest(
                tool_name=tool_name,
                arguments=arguments or {},
            ),
            user=self.user,
        )

    def test_reads_program_list_detail_calendar_and_inbox(self):
        programs = self.execute(
            TOOL_LIST_USER_PROGRAMS,
            {"search": "fuerza", "limit": 5},
        )
        detail = self.execute(TOOL_READ_PROGRAM, {"program_id": self.program.id})
        calendar = self.execute(TOOL_READ_CALENDARIZATION, {"history_limit": 3})
        inbox = self.execute(TOOL_LIST_INBOX_ITEMS, {"scope": "received", "limit": 5})

        self.assertEqual(programs.status, AssistantToolStatus.OK)
        self.assertEqual(programs.data["programs"][0]["id"], self.program.id)
        self.assertEqual(detail.data["program"]["slots"][0]["dailyplan_id"], self.dailyplan.id)
        self.assertEqual(
            calendar.data["calendarization"]["current"]["id"],
            self.calendarization.id,
        )
        self.assertEqual(inbox.data["inbox_items"][0]["kind"], "dailyplan")
        self.assertFalse(detail.metadata["writes_allowed"])

    def test_reads_account_billing_without_exposing_provider_mutations(self):
        result = self.execute(TOOL_READ_ACCOUNT_BILLING_CONTEXT)

        self.assertEqual(result.status, AssistantToolStatus.OK)
        self.assertIn("plan_name", result.data["account_billing"])
        self.assertTrue(
            result.data["navigation_policy"]["checkout_requires_trusted_ui"]
        )
        self.assertTrue(
            result.data["navigation_policy"]["assistant_may_not_call_payment_provider"]
        )
