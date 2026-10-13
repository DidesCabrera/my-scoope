import assert from "node:assert/strict";
import test from "node:test";

import type { CalendarizedDayDetail } from "../src/api/types";
import {
  publishCalendarizedDayUpdate,
  subscribeToCalendarizedDayUpdates,
} from "../src/components/calendarization/calendarized-day-updates";

test("calendarized day updates reach mounted projections and stop after unsubscribe", () => {
  const received: CalendarizedDayDetail[] = [];
  const day = {
    id: 42,
    calendar_date: "2026-10-12",
    week_number: 1,
    day_number: 1,
    has_plan: true,
    meal_execution: [],
    plan_name: "Plan activo",
    plan_snapshot: {
      name: "Plan activo",
      meals: [{ key: "meal:1", name: "Cena", hour: "21:15", foods: [], totals: {} }],
      totals: {},
    },
  } as CalendarizedDayDetail;

  const unsubscribe = subscribeToCalendarizedDayUpdates((updated) => received.push(updated));
  publishCalendarizedDayUpdate(day);
  unsubscribe();
  publishCalendarizedDayUpdate({ ...day, plan_name: "No debe recibirse" });

  assert.deepEqual(received, [day]);
});
