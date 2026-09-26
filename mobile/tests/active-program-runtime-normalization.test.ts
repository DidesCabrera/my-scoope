import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import {
  normalizeActiveProgramData,
  normalizeCalendarizedDayDetail,
  normalizeDailyPlanSnapshot,
} from "../src/components/calendarization/runtime-normalization";

test("active program responses default missing render collections", () => {
  const program = normalizeActiveProgramData({
    calendarization: {
      id: 7,
      program_name: "Programa",
      status: "active",
      start_date: "2026-09-01",
      end_date: "2026-09-28",
    },
    days: null,
    weeks: { unexpected: true },
  });

  assert.deepEqual(program.days, []);
  assert.deepEqual(program.weeks, []);
  assert.deepEqual(program.indicators, []);
  assert.equal(program.calendarization?.program_name, "Programa");
});

test("calendarized day details cannot expose malformed snapshot arrays to React Native", () => {
  const detail = normalizeCalendarizedDayDetail({
    id: 42,
    calendar_date: "2026-09-25",
    week_number: 1,
    day_number: 4,
    has_plan: true,
    plan_name: "Plan activo",
    meal_execution: null,
    plan_snapshot: {
      name: "Plan activo",
      meals: [null, "legacy", { key: "breakfast", name: "Desayuno", foods: { legacy: true } }],
      totals: [],
    },
  });

  assert.ok(detail);
  assert.deepEqual(detail.meal_execution, []);
  assert.equal(detail.plan_snapshot?.meals?.length, 1);
  assert.deepEqual(detail.plan_snapshot?.meals?.[0].foods, []);
  assert.equal(detail.plan_snapshot?.totals, undefined);
});

test("non-object snapshots become an empty day instead of crashing the route", () => {
  assert.equal(normalizeDailyPlanSnapshot("legacy snapshot"), null);
  assert.equal(normalizeCalendarizedDayDetail({ id: "bad" }), null);
});

test("active program routes normalize every response before storing render state", async () => {
  const program = await readFile(path.resolve(process.cwd(), "src/app/program/index.tsx"), "utf8");
  const planning = await readFile(path.resolve(process.cwd(), "src/components/calendarization/calendarized-program-planning.tsx"), "utf8");

  assert.match(program, /setProgram\(normalizeActiveProgramData\(await apiRequest<ActiveProgramData>/);
  assert.match(program, /setProgram\(normalizeActiveProgramData\(nextProgram\)\)/);
  assert.match(planning, /setDetail\(normalizeCalendarizedDayDetail\(nextDetail\)\)/);
  assert.match(planning, /setDetail\(normalizeCalendarizedDayDetail\(await apiRequest<CalendarizedDayDetail>/);
});
