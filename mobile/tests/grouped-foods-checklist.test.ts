import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("accumulated food lists expose the shared check column in active and library surfaces", async () => {
  const groupedFoods = await readFile(path.resolve(process.cwd(), "src/components/panels/grouped-foods-card.tsx"), "utf8");
  assert.match(groupedFoods, /useState<Set<string>>/);
  assert.match(groupedFoods, /const checklist = preparation \?\?/);
  assert.match(groupedFoods, /<FoodPanels items=\{items\} preparation=\{checklist\} showPreparationColumn/);

  const accumulatedListSurfaces = [
    "src/components/libraries/library-detail-screen.tsx",
    "src/components/libraries/program-detail-preview.tsx",
    "src/components/calendarization/calendarized-program-planning.tsx",
    "src/app/program/days/[id].tsx",
  ];
  for (const relativePath of accumulatedListSurfaces) {
    const source = await readFile(path.resolve(process.cwd(), relativePath), "utf8");
    assert.match(source, /<GroupedFoodsCard/);
  }
});

test("shopping commitment previews and saved lists use the shared check column", async () => {
  for (const relativePath of [
    "src/app/calendar/commitments.tsx",
    "src/components/calendarization/calendar-plan-editor.tsx",
  ]) {
    const source = await readFile(path.resolve(process.cwd(), relativePath), "utf8");
    assert.ok(source.includes("<GroupedFoodsCard"));
    assert.ok(!source.includes("showChecklist={false}"));
  }
});
