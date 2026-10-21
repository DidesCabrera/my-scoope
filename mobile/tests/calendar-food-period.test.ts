import assert from "node:assert/strict";
import test from "node:test";

import { validCalendarFoodPeriod } from "../src/components/calendarization/calendar-food-period";

test("shopping food period requires two ordered dates", () => {
  assert.equal(validCalendarFoodPeriod("", "2026-10-21"), false);
  assert.equal(validCalendarFoodPeriod("2026-10-22", "2026-10-21"), false);
  assert.equal(validCalendarFoodPeriod("2026-10-21", "2026-10-21"), true);
});

test("shopping food period accepts up to 366 inclusive days", () => {
  assert.equal(validCalendarFoodPeriod("2026-01-01", "2027-01-01"), true);
  assert.equal(validCalendarFoodPeriod("2026-01-01", "2027-01-02"), false);
});
