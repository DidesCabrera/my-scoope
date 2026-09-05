from datetime import timedelta
from zoneinfo import ZoneInfo

from django.test import override_settings
from django.utils import timezone

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import (
    CalendarizedDay,
    ProgramCalendarization,
    ScheduledNotificationEvent,
)


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPICalendarizationReminderTests(AuthenticatedMobileAPITestCase):
    def test_today_reminders_exclude_elapsed_events_and_return_a_bounded_future_window(self):
        today = timezone.localdate(timezone=ZoneInfo("UTC"))
        current_time = timezone.now()
        calendarization = ProgramCalendarization.objects.create(
            user=self.user,
            program_name_snapshot="Programa con recordatorios",
            start_date=today,
            end_date=today + timedelta(days=30),
            timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
            meal_notifications_enabled=True,
        )
        day = CalendarizedDay.objects.create(
            calendarization=calendarization,
            calendar_date=today,
            week_number=1,
            day_number=1,
        )

        for index in range(5):
            scheduled_for = current_time - timedelta(minutes=index + 1)
            ScheduledNotificationEvent.objects.create(
                calendarization=calendarization,
                calendarized_day=day,
                event_type=ScheduledNotificationEvent.TYPE_MEAL_REMINDER,
                event_key=f"past:{index}",
                meal_snapshot_key=f"meal-past-{index}",
                local_scheduled_date=today,
                local_scheduled_time=scheduled_for.time(),
                timezone_name="UTC",
                scheduled_for_utc=scheduled_for,
                available_until_utc=scheduled_for + timedelta(minutes=15),
            )
        for index in range(65):
            scheduled_for = current_time + timedelta(minutes=index + 10)
            ScheduledNotificationEvent.objects.create(
                calendarization=calendarization,
                calendarized_day=day,
                event_type=ScheduledNotificationEvent.TYPE_MEAL_REMINDER,
                event_key=f"future:{index}",
                meal_snapshot_key=f"meal-future-{index}",
                local_scheduled_date=today,
                local_scheduled_time=scheduled_for.time(),
                timezone_name="UTC",
                scheduled_for_utc=scheduled_for,
                available_until_utc=scheduled_for + timedelta(minutes=15),
            )

        response = self.client.get("/api/v1/today")

        self.assertEqual(response.status_code, 200)
        upcoming = response.json()["data"]["reminders"]["upcoming"]
        self.assertEqual(len(upcoming), 60)
        self.assertEqual(upcoming[0]["event_key"], "future:0")
        self.assertEqual(upcoming[-1]["event_key"], "future:59")
        self.assertNotIn("past:0", {event["event_key"] for event in upcoming})
