import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string) {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("calendar daily plan cards reuse the canonical meal panels", async () => {
  const [previewCard, selection, dayEditor, calendarizedCard] = await Promise.all([
    source("src/components/calendarization/daily-plan-preview-card.tsx"),
    source("src/components/calendarization/calendar-select-plans-screen.tsx"),
    source("src/components/calendarization/calendar-plan-editor.tsx"),
    source("src/components/calendarization/calendarized-daily-plan-card.tsx"),
  ]);

  assert.match(previewCard, /<MealPanels dailyPlanId=\{item\.id\} items=\{item\.panel\.meals\} nestedScroll showEditTab=\{false\} \/>/);
  assert.match(selection, /<DailyPlanPreviewCard item=\{selected\} \/>/);
  assert.match(selection, /plans\.map\(\(plan\) => <DailyPlanPreviewCard/);
  assert.match(selection, /<SnapshotMealPanels items=\{\(snapshot\.meals \?\? \[\]\)\.map/);
  assert.match(dayEditor, /day\.has_plan && day\.plan_snapshot \? <CalendarizedDailyPlanCard/);
  assert.match(dayEditor, /plans\.map\(\(plan\) => <DailyPlanPreviewCard/g);
  assert.match(calendarizedCard, /additionalActions\?: ReactNode/);
  assert.match(calendarizedCard, /<MealPanels[\s\S]*nestedScroll[\s\S]*showEditTab=\{false\}/);
});
