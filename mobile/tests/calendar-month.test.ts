import assert from "node:assert/strict";
import test from "node:test";

import { monthKeyFromDate, monthLabel, monthWindow, shiftMonth } from "../src/components/calendarization/calendar-month";

test("monthly window starts on Monday and includes all dates of the month", () => {
  assert.deepEqual(monthWindow("2026-10"), { startDate: "2026-09-28", days: 35 });
  assert.deepEqual(monthWindow("2026-11"), { startDate: "2026-10-26", days: 42 });
  assert.deepEqual(monthWindow("2021-02"), { startDate: "2021-02-01", days: 28 });
});

test("month navigation crosses years and keeps a readable label", () => {
  assert.equal(monthKeyFromDate("2026-10-20"), "2026-10");
  assert.equal(shiftMonth("2026-12", 1), "2027-01");
  assert.equal(shiftMonth("2027-01", -1), "2026-12");
  assert.equal(monthLabel("2026-10"), "Octubre de 2026");
});
