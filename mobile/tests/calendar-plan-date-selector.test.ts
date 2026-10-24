import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("individual plan scheduling uses the commitment-style calendar selector", async () => {
  const source = await readFile(path.resolve(process.cwd(), "src/components/calendarization/calendar-select-plans-screen.tsx"), "utf8");

  assert.doesNotMatch(source, /NativeDateTimeField/);
  assert.match(source, /createCalendarMonthCache\(apiRequest\)/);
  assert.match(source, /monthLabel\(visibleMonth\)/);
  assert.match(source, /accessibilityRole="checkbox"/);
  assert.match(source, /gridDateSelected: \{ backgroundColor: `\$\{tokens\.color\.dailyPlan\}33`, borderColor: tokens\.color\.dailyPlan \}/);
  assert.match(source, /gridDateWithPlan: \{ backgroundColor: `\$\{tokens\.color\.dailyPlan\}33` \}/);
  assert.match(source, /setSelectedDates\(\(current\) => \[\.\.\.current, day\.calendar_date\]\)/);
  assert.match(source, /title="Planes que serán reemplazados"/);
  assert.match(source, /replacementDays\.map\(\(day\) => \{[\s\S]*return <NutritionEntityCard/);
  assert.match(source, /Promise\.all\(selectedDateList\.map/);
  assert.ok(source.indexOf("styles.calendarSection") < source.lastIndexOf("<NutritionEntityCard"));
});
