import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("calendar month loading preserves the calendar footprint and plan dates use main text", async () => {
  const source = await readFile(path.resolve(process.cwd(), "src/components/calendarization/calendar-overview-screen.tsx"), "utf8");
  assert.match(source, /function CalendarMonthPlaceholder\(\)[\s\S]*Array\.from\(\{ length: 42 \}/);
  assert.match(source, /!monthDays\.length && !monthError \? <CalendarMonthPlaceholder \/>/);
  assert.match(source, /gridPlaceholderDate: \{[^}]*minHeight: 38[^}]*width: "13\.5%"/);
  assert.match(source, /gridNumberWithPlan: \{ color: tokens\.color\.textMain, fontWeight: "700" \}/);
  assert.ok(source.indexOf("styles.calendarSection") < source.indexOf("styles.summaryRow"));
  assert.ok(source.indexOf("styles.summaryRow") < source.indexOf("styles.calendarizeActions"));
  assert.match(source, /calendarSection: \{ marginBottom: 12, marginTop: -12/);
  assert.match(source, /<Button icon=\{<EntityIcon entity="dailyPlan" \/>\} label="Calendarizar planes"/);
});
