import assert from "node:assert/strict";
import test from "node:test";

import type { CalendarDay } from "../src/api/calendar-types";
import { groupCalendarDaysByIsoWeek } from "../src/components/calendarization/calendar-weeks";

function day(calendar_date: string): CalendarDay {
  return { calendar_date, has_execution: false, has_plan: false, id: null, plan_name: "", source_kind: null, source_program_name: null };
}

test("future dates split at Monday and preserve a partial current week", () => {
  const groups = groupCalendarDaysByIsoWeek([
    day("2026-10-24"),
    day("2026-10-25"),
    day("2026-10-26"),
    day("2026-10-27"),
    day("2026-11-01"),
    day("2026-11-02"),
  ]);

  assert.deepEqual(groups.map(({ weekNumber, days }) => ({ weekNumber, dates: days.map((item) => item.calendar_date) })), [
    { weekNumber: 43, dates: ["2026-10-24", "2026-10-25"] },
    { weekNumber: 44, dates: ["2026-10-26", "2026-10-27", "2026-11-01"] },
    { weekNumber: 45, dates: ["2026-11-02"] },
  ]);
});
