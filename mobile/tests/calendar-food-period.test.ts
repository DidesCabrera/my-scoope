import assert from "node:assert/strict";
import test from "node:test";

import { calendarFoodDayRole, selectCalendarFoodDate, validCalendarFoodPeriod } from "../src/components/calendarization/calendar-food-period";

test("shopping food period requires two ordered dates", () => {
  assert.equal(validCalendarFoodPeriod("", "2026-10-21"), false);
  assert.equal(validCalendarFoodPeriod("2026-10-22", "2026-10-21"), false);
  assert.equal(validCalendarFoodPeriod("2026-10-21", "2026-10-21"), true);
});

test("shopping food period accepts up to 366 inclusive days", () => {
  assert.equal(validCalendarFoodPeriod("2026-01-01", "2027-01-01"), true);
  assert.equal(validCalendarFoodPeriod("2026-01-01", "2027-01-02"), false);
});

test("calendar range chooses start, inclusive end, then starts a new range", () => {
  assert.deepEqual(selectCalendarFoodDate("", "", "2026-10-30"), { start: "2026-10-30", end: "", tooLong: false });
  assert.deepEqual(selectCalendarFoodDate("2026-10-30", "", "2026-11-02"), { start: "2026-10-30", end: "2026-11-02", tooLong: false });
  assert.equal(calendarFoodDayRole("2026-10-30", "2026-10-30", "2026-11-02"), "start");
  assert.equal(calendarFoodDayRole("2026-11-01", "2026-10-30", "2026-11-02"), "between");
  assert.equal(calendarFoodDayRole("2026-11-02", "2026-10-30", "2026-11-02"), "end");
  assert.deepEqual(selectCalendarFoodDate("2026-10-30", "2026-11-02", "2026-11-05"), { start: "2026-11-05", end: "", tooLong: false });
});

test("calendar range supports one day, earlier restart, and rejects more than 366 days", () => {
  assert.deepEqual(selectCalendarFoodDate("2026-10-21", "", "2026-10-21"), { start: "2026-10-21", end: "2026-10-21", tooLong: false });
  assert.equal(calendarFoodDayRole("2026-10-21", "2026-10-21", "2026-10-21"), "single");
  assert.deepEqual(selectCalendarFoodDate("2026-10-21", "", "2026-10-19"), { start: "2026-10-19", end: "", tooLong: false });
  assert.deepEqual(selectCalendarFoodDate("2026-01-01", "", "2027-01-02"), { start: "2026-01-01", end: "", tooLong: true });
});
