import assert from "node:assert/strict";
import test from "node:test";

import { currentWeekDays } from "../src/components/calendarization/current-week";

test("current week starts on Monday and marks the server-provided local date", () => {
  const days = currentWeekDays("2026-08-28");
  assert.deepEqual(days.map((day) => day.date), [
    "2026-08-24",
    "2026-08-25",
    "2026-08-26",
    "2026-08-27",
    "2026-08-28",
    "2026-08-29",
    "2026-08-30",
  ]);
  assert.deepEqual(days.map((day) => day.label), ["L", "M", "X", "J", "V", "S", "D"]);
  assert.equal(days.find((day) => day.isToday)?.date, "2026-08-28");
});

test("current week remains correct across a month boundary", () => {
  assert.deepEqual(currentWeekDays("2026-09-01").map((day) => day.date), [
    "2026-08-31",
    "2026-09-01",
    "2026-09-02",
    "2026-09-03",
    "2026-09-04",
    "2026-09-05",
    "2026-09-06",
  ]);
});
