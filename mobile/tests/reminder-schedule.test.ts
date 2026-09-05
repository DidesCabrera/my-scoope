import assert from "node:assert/strict";
import test from "node:test";

import type { ReminderSettings } from "../src/api/types";
import {
  LOCAL_REMINDER_LIMIT,
  localReminderEvents,
  localReminderIdentifier,
  shouldScheduleNativeReminders,
} from "../src/notifications/reminder-schedule";

const now = Date.parse("2026-09-02T12:00:00.000Z");

function reminderSettings(upcoming: ReminderSettings["upcoming"]): ReminderSettings {
  return {
    timezone_name: "America/Santiago",
    daily_notification_time: "07:00:00",
    daily_notifications_enabled: true,
    meal_notifications_enabled: true,
    upcoming,
  };
}

function event(eventKey: string, scheduledFor: string): ReminderSettings["upcoming"][number] {
  return {
    event_key: eventKey,
    event_type: "meal_reminder",
    meal_key: eventKey,
    local_date: "2026-09-02",
    local_time: "09:00:00",
    scheduled_for_utc: scheduledFor,
    status: "pending",
  };
}

test("local reminder projection excludes invalid and elapsed events and sorts future events", () => {
  const projected = localReminderEvents(reminderSettings([
    event("later", "2026-09-02T14:00:00.000Z"),
    event("elapsed", "2026-09-02T11:59:59.000Z"),
    event("invalid", "not-a-date"),
    event("too-close", "2026-09-02T12:00:04.000Z"),
    event("first", "2026-09-02T13:00:00.000Z"),
  ]), now);

  assert.deepEqual(projected.map((item) => item.event_key), ["first", "later"]);
  assert.equal(projected[0].scheduledAt.toISOString(), "2026-09-02T13:00:00.000Z");
});

test("local reminder projection stays below the native pending-request capacity", () => {
  const upcoming = Array.from({ length: LOCAL_REMINDER_LIMIT + 5 }, (_, index) => (
    event(`meal-${index}`, new Date(now + (index + 1) * 60_000).toISOString())
  ));

  const projected = localReminderEvents(reminderSettings(upcoming), now);

  assert.equal(projected.length, LOCAL_REMINDER_LIMIT);
  assert.equal(projected.at(-1)?.event_key, `meal-${LOCAL_REMINDER_LIMIT - 1}`);
  assert.equal(localReminderIdentifier("meal-4"), "myscoope-calendarization:meal-4");
});

test("only active and scheduled programs may keep native reminders", () => {
  assert.equal(shouldScheduleNativeReminders("active"), true);
  assert.equal(shouldScheduleNativeReminders("scheduled"), true);
  assert.equal(shouldScheduleNativeReminders("paused"), false);
  assert.equal(shouldScheduleNativeReminders("cancelled"), false);
  assert.equal(shouldScheduleNativeReminders("completed"), false);
  assert.equal(shouldScheduleNativeReminders(null), false);
});
