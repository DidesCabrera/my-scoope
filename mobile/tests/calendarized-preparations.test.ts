import assert from "node:assert/strict";
import test from "node:test";
import path from "node:path";

import { readTestFile } from "./support/source-contract";

test("calendarized snapshot adapters preserve preparation identity", async () => {
  const adapter = await readTestFile(path.resolve(process.cwd(), "src/components/calendarization/presentation-adapters.ts"), "utf8");
  assert.match(adapter, /food\.component_type === "preparation"/);
  assert.match(adapter, /source_preparation_id/);
  assert.match(adapter, /kind: food\.kind/);
});

test("active meal detail exposes preparation navigation and instance actions", async () => {
  const detail = await readTestFile(path.resolve(process.cwd(), "src/app/program/days/[id]/meals/[mealKey].tsx"), "utf8");
  const picker = await readTestFile(path.resolve(process.cwd(), "src/app/pickers/preparation-to-meal.tsx"), "utf8");
  assert.match(detail, /component\.kind === "preparation" \? preparationEditing : foodEditing/);
  assert.match(detail, /label="\+ Agregar preparación"/);
  assert.match(picker, /preparations\$\{snapshotKey/);
  assert.match(detail, /food\.kind === "preparation" \? `\/libraries\/preparations/);
});
