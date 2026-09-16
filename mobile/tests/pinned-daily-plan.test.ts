import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { assertSourceMatch, readTestFile } from "./support/source-contract";

test("Home creates or presents one live pinned daily plan", async () => {
  const home = await readTestFile(path.resolve(process.cwd(), "src/app/today.tsx"), "utf8");
  const card = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/pinned-daily-plan-card.tsx"), "utf8");

  assertSourceMatch(home, /Registra tus comidas en un nuevo Plan/);
  assertSourceMatch(home, /label="Crear un plan para hoy"/);
  assertSourceMatch(home, /apiRequest<TodayData>\("\/api\/v1\/today\/pinned-plan", \{ method: "POST" \}\)/);
  assertSourceMatch(home, /<PinnedDailyPlanCard editing=\{pinnedMealEditing\} item=\{today\.pinned_plan\}/);
  assertSourceMatch(card, /<EntityCard actions=\{detailAction\} entity="dailyPlan" eyebrow="PLAN DE HOY" title=\{item\.name\}>/);
  assertSourceMatch(card, /label="Ir al detalle del plan"/);
  assertSourceMatch(card, /router\.push\(`\/libraries\/daily-plans\/\$\{item\.id\}` as Href\)/);
  assertSourceMatch(card, /addMealAction: \{ marginTop: tokens\.spacing\.md \}/);
  assertSourceMatch(card, /label="\+ Agregar Comida"/);
  assert.doesNotMatch(card, /<EntityCard[^>]*indicators=/);
});

test("pinned library plans reuse daily completion and food preparation controls", async () => {
  const detail = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");
  const cards = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/entity-panels.tsx"), "utf8");
  const adherence = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/meal-adherence-check-in.tsx"), "utf8");

  assertSourceMatch(detail, /Fijar como Plan de hoy/);
  assertSourceMatch(detail, /<DailyMealCompletionCard/);
  assertSourceMatch(detail, /pinnedTracking=\{isPinnedPlan/);
  assertSourceMatch(cards, /<MealCompletionToggleCard/);
  assertSourceMatch(cards, /preparation=\{pinnedTracking/);
  assertSourceMatch(adherence, /mode === "pinned"/);
  assertSourceMatch(adherence, /\/api\/v1\/today\/pinned-plan\/meals/);
});
