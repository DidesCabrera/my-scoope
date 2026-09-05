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

test("meal cards nested in a daily plan expose remove and detail only", async () => {
  const cards = await source("src/components/libraries/entity-panels.tsx");
  const detail = await source("src/components/libraries/library-detail-screen.tsx");

  assert.match(cards, /label: "Quitar comida"/);
  assert.match(cards, /Ver detalle de/);
  assert.match(detail, /<DailyPlanMealCards[^>]*items=\{item\.panel\.meals\}[^>]*onRemove=/);
});
