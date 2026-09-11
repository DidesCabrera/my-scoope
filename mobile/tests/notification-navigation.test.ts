import assert from "node:assert/strict";
import test from "node:test";

import type { ReminderSettings } from "../src/api/types";
import {
  notificationRoute,
  notificationRouteForReminder,
} from "../src/notifications/notification-navigation";

const reminder: ReminderSettings["upcoming"][number] = {
  calendarized_day_id: 42,
  event_key: "meal:42:dailyplan_meal:7",
  event_type: "meal_reminder",
  local_date: "2026-09-11",
  local_time: "13:00:00",
  meal_key: "dailyplan_meal:7",
  scheduled_for_utc: "2026-09-11T16:00:00Z",
  status: "pending",
};

test("meal reminders open the calendarized meal detail", () => {
  assert.equal(
    notificationRouteForReminder(reminder),
    "/program/days/42/meals/dailyplan_meal%3A7",
  );
});

test("notification responses support local and APNs routing data", () => {
  assert.equal(
    notificationRoute({ url: "/program/days/42/meals/dailyplan_meal%3A7" }),
    "/program/days/42/meals/dailyplan_meal%3A7",
  );
  assert.equal(
    notificationRoute({ myscoope: { url: "/program/days/42/meals/dailyplan_meal%3A7" } }),
    "/program/days/42/meals/dailyplan_meal%3A7",
  );
});

test("notification responses reject external or unsupported destinations", () => {
  assert.equal(notificationRoute(undefined), "/today");
  assert.equal(notificationRoute({ url: "https://malicious.example/path" }), "/today");
  assert.equal(notificationRoute({ url: "/account" }), "/today");
});
