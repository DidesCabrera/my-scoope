import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { readTestFile } from "./support/source-contract";

test("program week detail presents planning before food and comparison insights", async () => {
  const source = await readTestFile(
    path.resolve(process.cwd(), "src/components/libraries/program-detail-preview.tsx"),
    "utf8",
  );
  const weekDetail = source.slice(
    source.indexOf("export function ProgramWeekDetail"),
    source.indexOf("type ProgramDetailPreviewProps"),
  );

  const dailyPlans = weekDetail.indexOf('title="Planes diarios esta semana"');
  const daysGrid = weekDetail.indexOf("<ProgramDaysGrid");
  const foods = weekDetail.indexOf('title="Alimentos en esta semana"');
  const foodPanels = weekDetail.indexOf("<FoodPanels");
  const dividerAfterFoods = weekDetail.indexOf('<SectionDivider spacing="compact" tone="soft" />', foodPanels);
  const weeklyChart = weekDetail.indexOf("<ProgramMetricPreview");
  const comparison = weekDetail.indexOf('title="Tabla de comparación entre planes diarios"');

  assert.ok(dailyPlans >= 0);
  assert.ok(dailyPlans < daysGrid);
  assert.ok(daysGrid < foods);
  assert.ok(foods < weeklyChart);
  assert.ok(weeklyChart < comparison);
  assert.ok(foods < foodPanels);
  assert.ok(foodPanels < dividerAfterFoods);
  assert.ok(dividerAfterFoods < weeklyChart);
  assert.ok(!weekDetail.includes('<SectionDivider spacing="compact" tone="soft" />\n        <SectionHeading detail={`${filledDaysCount} asignados`} title="Planes diarios esta semana"'));
});
