import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string) {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("entity cards expose a shared left-aligned panel visibility control", async () => {
  const product = await source("src/components/ui/product.tsx");
  const nutritionCard = await source("src/components/nutrition/nutrition-entity-card.tsx");

  assert.match(product, /export function EntityCardPanelToggle/);
  assert.match(product, /accessibilityState=\{\{ expanded \}\}/);
  assert.match(product, /expanded \? "Ver menos" : "Ver más"/);
  assert.match(product, /<EntityCardActions leading=\{panelToggle \? <EntityCardPanelToggle/);
  assert.match(product, /entityCardActions: \{[^}]*justifyContent: "space-between"/);
  assert.match(nutritionCard, /const \[panelExpanded, setPanelExpanded\] = useState\(true\)/);
  assert.match(nutritionCard, /children && \(!hasCollapsiblePanel \|\| panelExpanded\)/);
});

test("library entity cards collapse their corresponding detail panels", async () => {
  const libraryCard = await source("src/components/libraries/library-card.tsx");
  const foodPanel = await source("src/components/panels/food-nutrition-panel.tsx");
  const programCard = await source("src/components/libraries/program-child-card.tsx");

  assert.match(libraryCard, /<NutritionEntityCard[\s\S]*?collapsiblePanel/);
  assert.match(libraryCard, /item\.entity === "food" \? <FoodNutritionPanel/);
  for (const nutrient of ["Información nutricional", "NutritionFactsTable"]) assert.match(foodPanel, new RegExp(nutrient));
  assert.match(programCard, /const \[metricsExpanded, setMetricsExpanded\] = useState\(true\)/);
  assert.match(programCard, /metricsExpanded \? <ProgramMetricPreview/);
  assert.match(programCard, /<EntityCardPanelToggle expanded=\{metricsExpanded\}/);
});

test("in-progress meal and daily-plan cards use the shared collapsible panel", async () => {
  for (const relativePath of [
    "src/components/calendarization/calendarized-daily-plan-card.tsx",
    "src/components/calendarization/pinned-daily-plan-card.tsx",
    "src/components/libraries/entity-panels.tsx",
    "src/components/libraries/program-daily-plan-preview.tsx",
    "src/app/program/days/[id].tsx",
  ]) {
    assert.match(await source(relativePath), /<NutritionEntityCard[\s\S]*?collapsiblePanel/);
  }
});
