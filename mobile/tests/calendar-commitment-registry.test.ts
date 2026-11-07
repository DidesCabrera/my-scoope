import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import type { CalendarCommitment, CalendarDay } from "../src/api/calendar-types";
import { commitmentsForMonth } from "../src/components/calendarization/calendar-commitment-registry";
import { readTestFile } from "./support/source-contract";

function day(date: string, kind: CalendarCommitment["kind"]): CalendarDay {
  return {
    calendar_date: date, commitments: [{ id: Number(date.slice(-2)), calendar_date: date, kind, note: "", food_period_start: null, food_period_end: null, food_plans_count: 0, foods: [] }],
    has_execution: false, has_plan: false, id: null, plan_name: "", source_kind: null, source_program_name: null,
  };
}

test("monthly commitment filters retain the visible month and include today", () => {
  const days = [day("2026-09-30", "cooking"), day("2026-10-20", "shopping"), day("2026-10-27", "cooking"), day("2026-10-31", "training"), day("2026-11-01", "nutritionist")];
  assert.deepEqual(commitmentsForMonth(days, "2026-10", "2026-10-27", "all", "upcoming").map((item) => item.calendar_date), ["2026-10-27", "2026-10-31"]);
  assert.deepEqual(commitmentsForMonth(days, "2026-10", "2026-10-27", "all", "all").map((item) => item.calendar_date), ["2026-10-20", "2026-10-27", "2026-10-31"]);
  assert.deepEqual(commitmentsForMonth(days, "2026-10", "2026-10-27", "cooking", "upcoming").map((item) => item.calendar_date), ["2026-10-27"]);
});

test("calendar opens a day directly and contains both consolidated sections", async () => {
  const source = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/calendar-overview-screen.tsx"), "utf8");
  const calendar = source.indexOf("<CalendarMonthCalendar");
  const metrics = source.indexOf("Próximos compromisos</Text>", calendar);
  const addActions = source.indexOf('label="Añadir minuta"', metrics);
  const minutes = source.indexOf('title="Mis minutas programadas"', addActions);
  const upcoming = source.indexOf('title="Próximas minutas"', minutes);
  const commitments = source.indexOf('title="Mis compromisos"', upcoming);
  const filters = source.indexOf('accessibilityLabel="Tipos de compromisos"', commitments);
  const list = source.indexOf('Compromisos de ${visibleMonth', filters);
  const week = source.indexOf('title="Semana actual"', list);
  assert.ok(calendar < metrics && metrics < addActions && addActions < minutes && minutes < upcoming && upcoming < commitments && commitments < filters && filters < list && list < week);
  assert.match(source, /onOpenDay=\{openDay\}/);
  assert.match(source, /CalendarDaySectionHeading date=\{overview\.local_date\} today=\{overview\.local_date\}/);
  assert.doesNotMatch(source, /todayCard|todaySection|\/calendar\/registry|\/calendar\/plans/);
});

test("removed calendar subviews redirect and commitment notifications return to calendar", async () => {
  for (const route of ["registry", "plans"]) {
    const source = await readTestFile(path.resolve(process.cwd(), `src/app/calendar/${route}.tsx`), "utf8");
    assert.match(source, /<Redirect href="\/calendar" \/>/);
  }
  const notificationSource = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/commitment-notifications.tsx"), "utf8");
  assert.match(notificationSource, /fallback: "\/calendar"/);
});
