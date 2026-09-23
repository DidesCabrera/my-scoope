import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("program proposals allow review of every week and day before application", async () => {
  const program = await source("src/components/proposals/proposal-program-preview.tsx");
  const detail = await source("src/app/proposals/[id].tsx");
  assert.match(program, /length: program.duration_weeks/);
  assert.match(program, /item.week_number === week && item.day_number === dayNumber/);
  assert.match(program, /<ProposalMealCard/);
  assert.match(program, /program.warnings/);
  assert.match(detail, /<ProposalProgramPreview/);
  assert.match(detail, /libraries\/programs/);
});

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
  assert.match(detail, /<ProposalEvaluationContext current=\{proposal\.current_facts\} targets=\{proposal\.target_facts\} \/>/);
  assert.match(preview, /<FoodPanels/);
  assert.match(preview, /onOpenItem=\{onOpenFood \? \(food\) => \{ if \(food\.detailId != null\) onOpenFood\(food\.detailId\); \} : undefined\}/);
  assert.match(preview, /<MealPanels/);
  assert.doesNotMatch(preview, /projectedLabel: "Propuest[oa]"/);
  assert.match(preview, /icon: "clock"/);
  assert.doesNotMatch(preview, /indicators=\{\[\{ label: food\.unit/);
  assert.doesNotMatch(preview, /function Kpis/);
  assert.match(preview, /factsAreEqual/);
  assert.match(preview, /title="Contexto de la propuesta"/);
  assert.match(preview, /title="Punto de partida"/);
});

test("proposed entities expose progressive detail navigation", async () => {
  const entity = await source("src/app/proposals/[id]/entity.tsx");
  const meal = await source("src/app/proposals/[id]/entity/meals/[mealIndex].tsx");
  const typography = await source("src/components/ui/typography.tsx");

  assert.match(entity, /<EntityDetailPage/);
  assert.match(entity, /proposal\?\.dailyplan \? "Plan Diario Propuesto" : proposal\?\.meal \? "Comida Propuesta"/);
  assert.doesNotMatch(entity, /title: "Entidad propuesta"/);
  assert.match(entity, /<SectionDivider \/>[\s\S]*title="Detalle de cada Alimento"/);
  assert.match(entity, /<SectionDivider \/>[\s\S]*title="Detalle de cada Comida"/);
  assert.match(entity, /title="Detalle de cada Comida"/);
  assert.match(entity, /eyebrow=\{`Comida \$\{index \+ 1\}`\}/);
  assert.match(entity, /time=\{item\.hour\}/);
  assert.match(entity, /onOpenFood=\{\(foodId\) => router\.push\(`\/libraries\/foods\/\$\{foodId\}` as Href\)\}/);
  assert.match(entity, /\/proposals\/\$\{proposal\.id\}\/entity\/meals\//);
  assert.match(entity, /\/libraries\/foods\//);
  assert.match(entity, /<FoodPanels[\s\S]*?onOpenItem=\{\(food\) => \{ if \(food\.detailId != null\) router\.push\(`\/libraries\/foods\/\$\{food\.detailId\}` as Href\); \}\}/);
  assert.match(meal, /<EntityDetailPage/);
  assert.match(meal, /<SectionDivider \/>[\s\S]*title="Detalle de cada Alimento"/);
  assert.match(meal, /title="Detalle de cada Alimento"/);
  assert.match(meal, /icon: "clock"/);
  assert.match(meal, /\/libraries\/foods\//);
  assert.match(meal, /<FoodPanels[\s\S]*?onOpenItem=\{\(food\) => \{ if \(food\.detailId != null\) router\.push\(`\/libraries\/foods\/\$\{food\.detailId\}` as Href\); \}\}/);
  assert.doesNotMatch(meal, /subtitle=\{item\.note/);
  assert.match(typography, /normalizedTitle === "composición"/);
});

test("proposed meal food panel rows preserve library food identities", async () => {
  const preview = await source("src/components/proposals/proposal-preview.tsx");

  assert.match(preview, /detailId: food\.food_id \?\? undefined/);
});

test("meal details reuse food entity cards across library and calendarized contexts", async () => {
  const library = await source("src/components/libraries/library-detail-screen.tsx");
  const calendarized = await source("src/app/program/days/[id]/meals/[mealKey].tsx");
  const foodCards = await source("src/components/details/food-detail-card-list.tsx");

  assert.match(library, /title="Detalle de cada Alimento"><FoodDetailCardList/);
  assert.match(library, /\/libraries\/foods\/\$\{food\.detailId\}/);
  assert.match(calendarized, /title="Detalle de cada Alimento"><FoodDetailCardList/);
  assert.match(calendarized, /<SectionDivider \/><EntityDetailSection[^>]*title="Detalle de cada Alimento"/);
  assert.match(foodCards, /<NutritionEntityCard/);
  assert.match(foodCards, /subtitle=\{`\$\{item\.quantity\} \$\{item\.quantityUnit\}`\}/);
  assert.doesNotMatch(foodCards, /indicators=/);
});
