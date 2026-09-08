import assert from "node:assert/strict";
import test from "node:test";

import { compactDateLabel, compactMonthLabel, currentWeekDays, currentWeekRange, homePlanDateLabel, preferredCalendarizedDay } from "../src/components/calendarization/current-week";

test("compact dates omit the locale abbreviation period", () => {
  assert.equal(compactDateLabel("2026-08-28"), "28 ago");
  assert.equal(currentWeekRange("2026-09-01"), "31 ago — 6 sept");
});

test("compact month labels use three capitalized letters", () => {
  assert.equal(compactMonthLabel("2026-09-01"), "Sep");
  assert.equal(compactMonthLabel("2026-08-31"), "Ago");
});

test("home plan date combines weekday, day and three-letter month", () => {
  assert.equal(homePlanDateLabel("2026-09-08"), "martes 8 de sep");
});

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
  const days = currentWeekDays("2026-09-01");
  assert.deepEqual(days.map((day) => day.date), [
    "2026-08-31",
    "2026-09-01",
    "2026-09-02",
    "2026-09-03",
    "2026-09-04",
    "2026-09-05",
    "2026-09-06",
  ]);
  assert.deepEqual(days.map((day) => day.monthLabel), ["Ago", "Sep", "Sep", "Sep", "Sep", "Sep", "Sep"]);
});

test("active program selects today in the current week and day one in other weeks", () => {
  const days = [
    { calendar_date: "2026-09-08", day_number: 1, id: 1, week_number: 1 },
    { calendar_date: "2026-09-09", day_number: 2, id: 2, week_number: 1 },
    { calendar_date: "2026-09-15", day_number: 1, id: 3, week_number: 2 },
    { calendar_date: "2026-09-16", day_number: 2, id: 4, week_number: 2 },
  ];
  assert.equal(preferredCalendarizedDay(days, 1, "2026-09-09")?.id, 2);
  assert.equal(preferredCalendarizedDay(days, 2, "2026-09-09")?.id, 3);
});
