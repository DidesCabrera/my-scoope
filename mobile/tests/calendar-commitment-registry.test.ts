import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import type { CalendarCommitment, CalendarDay } from "../src/api/calendar-types";
import { commitmentsForUpcomingDays } from "../src/components/calendarization/calendar-commitment-registry";
import { readTestFile } from "./support/source-contract";

function day(date: string, kind: CalendarCommitment["kind"]): CalendarDay {
  return {
    calendar_date: date, commitments: [{ id: Number(date.slice(-2)), calendar_date: date, kind, note: "", food_period_start: null, food_period_end: null, food_plans_count: 0, foods: [] }],
    has_execution: false, has_plan: false, id: null, plan_name: "", source_kind: null, source_program_name: null,
  };
}

test("upcoming commitment filters include today and stop after seven days", () => {
  const days = [day("2026-09-30", "cooking"), day("2026-10-20", "shopping"), day("2026-10-27", "cooking"), day("2026-10-31", "training"), day("2026-11-01", "nutritionist")];
  assert.deepEqual(commitmentsForUpcomingDays(days, "2026-10-27", 7, "all").map((item) => item.calendar_date), ["2026-10-27", "2026-10-31", "2026-11-01"]);
  assert.deepEqual(commitmentsForUpcomingDays(days, "2026-10-27", 7, "cooking").map((item) => item.calendar_date), ["2026-10-27"]);
});

test("calendar opens a day directly and contains both consolidated sections", async () => {
  const source = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/calendar-overview-screen.tsx"), "utf8");
  const calendar = source.indexOf("<CalendarMonthCalendar");
  const metrics = source.indexOf("Minutas y compromisos programados</Text>", calendar);
  const addActions = source.indexOf('label="Añadir minuta"', metrics);
  const minutes = source.indexOf('title="Mis minutas programadas"', addActions);
  const commitments = source.indexOf('title="Mis compromisos programados"', minutes);
  const filters = source.indexOf('accessibilityLabel="Tipos de compromisos"', commitments);
  const list = source.indexOf('Próximos 7 días', filters);
  assert.ok(calendar < metrics && metrics < addActions && addActions < minutes && minutes < commitments && commitments < filters && filters < list);
  assert.ok(source.includes("onOpenDay={openDay}"));
  assert.ok(source.includes('label="Ver más fechas"'));
  assert.ok(source.includes('router.push("/calendar/future-commitments"'));
  assert.ok(source.includes("CalendarDaySectionHeading commitments={todayDay?.commitments} date={overview.local_date} hasPlan={todayDay?.has_plan} today={overview.local_date}"));
  assert.doesNotMatch(source, /todayCard|todaySection|\/calendar\/registry|\/calendar\/plans|Planes programados|Próxima minuta|title="Próximas minutas"|Compromisos asignados|Próximo compromiso|title="Mis compromisos"|title="Semana actual"|Fechas de la semana actual|Periodo de compromisos/);
});

test("removed calendar subviews redirect and commitment notifications return to calendar", async () => {
  for (const route of ["registry", "plans"]) {
    const source = await readTestFile(path.resolve(process.cwd(), `src/app/calendar/${route}.tsx`), "utf8");
    assert.ok(source.includes('<Redirect href="/calendar" />'));
  }
  const notificationSource = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/commitment-notifications.tsx"), "utf8");
  assert.ok(notificationSource.includes('fallback: "/calendar"'));
});

test("future commitments screen loads every commitment kind from today", async () => {
  const source = await readTestFile(path.resolve(process.cwd(), "src/app/calendar/future-commitments.tsx"), "utf8");
  assert.ok(source.includes('title="Compromisos futuros"'));
  assert.ok(source.includes("Promise.all(commitmentKinds.map"));
  assert.ok(source.includes("/api/v1/calendar/commitments?kind=${kind}&from_date=${overview.local_date}"));
  assert.ok(source.includes('accessibilityLabel="Tipos de compromisos futuros"'));
});
