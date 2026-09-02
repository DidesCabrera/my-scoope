import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(file: string): Promise<string> {
  return readFile(path.resolve(process.cwd(), file), "utf8");
}

test("library cards keep the server-projected web action matrix", async () => {
  const card = await source("src/components/libraries/library-card.tsx");
  const actions = await source("src/components/libraries/library-actions.tsx");
  const serverProjection = await source("../mobile_api/library_actions.py");

  assert.match(card, /item\.actions\?\.length/);
  assert.match(card, /<LibraryActions/);
  assert.match(actions, /const actions = item\.actions \?\? \[\]/);
  for (const action of ["Renombrar", "Duplicar", "Compartir", "Eliminar"]) {
    assert.match(serverProjection, new RegExp(action));
  }
});

test("program week cards expose duplicate and conditionally expose delete", async () => {
  const program = await source("src/components/libraries/program-detail-preview.tsx");

  assert.match(program, /<ContextCardActions/);
  assert.match(program, /label: "Duplicar semana"/);
  assert.match(program, /canRemoveWeek && onRemoveWeek/);
  assert.match(program, /label: "Eliminar semana"/);
  assert.match(program, /canRemoveWeek=\{weeksCount > 1\}/);
  assert.doesNotMatch(program, /onPress=\{\(\) => undefined\}/);
});

test("assigned daily plan cards expose replace, remove, and detail", async () => {
  const card = await source("src/components/libraries/program-daily-plan-preview.tsx");
  const parent = await source("src/components/libraries/program-detail-preview.tsx");

  assert.match(card, /label: "Reemplazar plan diario"/);
  assert.match(card, /label: "Quitar plan diario"/);
  assert.match(card, /Ir al detalle del plan/);
  assert.match(parent, /onReplace=\{onAssignDailyPlan/);
  assert.match(parent, /onRemove=\{onRemoveDailyPlan/);
  assert.doesNotMatch(card, /onPress=\{\(\) => undefined\}/);
});

test("meal cards nested in a daily plan preserve their slot context when opening detail", async () => {
  const cards = await source("src/components/libraries/entity-panels.tsx");
  const detail = await source("src/components/libraries/library-detail-screen.tsx");

  assert.match(cards, /label: "Quitar comida"/);
  assert.match(cards, /Ver detalle de/);
  assert.match(cards, /dailyPlanMealId/);
  assert.match(cards, /mealTime/);
  assert.match(detail, /<DailyPlanMealCards dailyPlanId=\{item\.id\} items=\{item\.panel\.meals\} onRemove=/);
});

test("meal detail actions expose the time editor for normal daily plans", async () => {
  const detail = await source("src/components/libraries/library-detail-screen.tsx");
  const actions = await source("src/components/libraries/library-actions.tsx");
  const timeActions = await source("src/components/calendarization/calendarized-entity-actions.tsx");

  assert.match(detail, /mealTimeChange=\{hasMealTimeContext/);
  assert.match(detail, /\/api\/v1\/library\/daily-plans\/\$\{contextDailyPlanId\}\/meals\/\$\{contextDailyPlanMealId\}/);
  assert.match(actions, /Cambiar hora/);
  assert.match(timeActions, /Hora de la comida/);
  assert.match(timeActions, /formato de 24 horas/);
});

test("active plan headers expose snapshot-scoped rename and time actions", async () => {
  const dayDetail = await source("src/app/program/days/[id].tsx");
  const mealDetail = await source("src/app/program/days/[id]/meals/[mealKey].tsx");
  const actions = await source("src/components/calendarization/calendarized-entity-actions.tsx");

  assert.match(dayDetail, /action: day\?\.has_plan/);
  assert.match(dayDetail, /<CalendarizedEntityActions/);
  assert.match(dayDetail, /\/api\/v1\/program\/days\/\$\{day\.id\}/);
  assert.match(mealDetail, /<CalendarizedEntityActions/);
  assert.match(mealDetail, /\/meals\/\$\{encodeURIComponent\(mealKey\)\}\/name/);
  assert.match(mealDetail, /timeChange=\{\{/);
  assert.match(actions, />Renombrar</);
  assert.match(actions, />Cambiar hora</);
});
