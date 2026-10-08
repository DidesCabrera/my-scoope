import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("search and active-meal note inputs use the panel background color", async () => {
  const panelSurface = await readFile(path.resolve(process.cwd(), "src/components/panels/panel-surface.tsx"), "utf8");
  assert.match(panelSurface, /surface: \{ backgroundColor: tokens\.color\.surfaceMuted/);

  for (const relativePath of [
    "src/components/libraries/library-list-screen.tsx",
    "src/components/pickers/composition-picker-screen.tsx",
  ]) {
    const source = await readFile(path.resolve(process.cwd(), relativePath), "utf8");
    assert.match(source, /searchField: \{[^}]*backgroundColor: tokens\.color\.surfaceMuted/);
  }

  const mealAdherence = await readFile(path.resolve(process.cwd(), "src/components/calendarization/meal-adherence-check-in.tsx"), "utf8");
  assert.match(mealAdherence, /noteInput: \{[^}]*backgroundColor: tokens\.color\.surfaceMuted/);
});
