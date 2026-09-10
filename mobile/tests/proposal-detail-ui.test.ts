import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string) {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("proposal detail uses the proposal and entity UI System contracts", async () => {
  const detail = await source("src/app/proposals/[id].tsx");
  const preview = await source("src/components/proposals/proposal-preview.tsx");

  assert.match(detail, /<ProposalDetailPage/);
  assert.match(detail, /<ProposalEntitySection/);
  assert.match(detail, /<ProposalMealCard/);
  assert.match(detail, /<ProposalDailyPlanCard/);
  assert.doesNotMatch(detail, /Creada por AI|Origen \$\{proposal\.source\}|Creada por \{proposal\.created_by_username\}/);

  assert.match(preview, /<NutritionEntityCard/);
  assert.match(preview, /<FoodPanels/);
  assert.match(preview, /<MealPanels/);
  assert.doesNotMatch(preview, /function Kpis/);
});

test("proposed entities expose progressive detail navigation", async () => {
  const entity = await source("src/app/proposals/[id]/entity.tsx");
  const meal = await source("src/app/proposals/[id]/entity/meals/[mealIndex].tsx");

  assert.match(entity, /<EntityDetailPage/);
  assert.match(entity, /title="Detalle de cada Comida"/);
  assert.match(entity, /\/proposals\/\$\{proposal\.id\}\/entity\/meals\//);
  assert.match(entity, /\/libraries\/foods\//);
  assert.match(meal, /<EntityDetailPage/);
  assert.match(meal, /title="Detalle de cada Alimento"/);
  assert.match(meal, /\/libraries\/foods\//);
});
