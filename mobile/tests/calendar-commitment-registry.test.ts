import assert from "node:assert/strict";
import test from "node:test";

import type { CalendarCommitment, CalendarDay } from "../src/api/calendar-types";
import { commitmentsForMonth } from "../src/components/calendarization/calendar-commitment-registry";

function day(date: string, kind: CalendarCommitment["kind"]): CalendarDay {
  return {
    calendar_date: date, commitments: [{ id: Number(date.slice(-2)), calendar_date: date, kind, note: "", food_period_start: null, food_period_end: null, food_plans_count: 0, foods: [] }],
    has_execution: false, has_plan: false, id: null, plan_name: "", source_kind: null, source_program_name: null,
  };
}

test("monthly commitment tabs keep the full month and include today in upcoming", () => {
  const days = [day("2026-09-30", "cooking"), day("2026-10-20", "shopping"), day("2026-10-27", "cooking"), day("2026-10-31", "training"), day("2026-11-01", "nutritionist")];
  assert.deepEqual(commitmentsForMonth(days, "2026-10", "2026-10-27", "all", "upcoming").map((item) => item.calendar_date), ["2026-10-27", "2026-10-31"]);
  assert.deepEqual(commitmentsForMonth(days, "2026-10", "2026-10-27", "all", "all").map((item) => item.calendar_date), ["2026-10-20", "2026-10-27", "2026-10-31"]);
  assert.deepEqual(commitmentsForMonth(days, "2026-10", "2026-10-27", "cooking", "upcoming").map((item) => item.calendar_date), ["2026-10-27"]);
  assert.deepEqual(commitmentsForMonth(days, "2026-09", "2026-10-27", "all", "upcoming"), []);
});
