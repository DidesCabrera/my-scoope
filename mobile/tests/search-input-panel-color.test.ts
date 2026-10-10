import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("the shared search field and active-meal note use the panel background color", async () => {
  const panelSurface = await readFile(path.resolve(process.cwd(), "src/components/panels/panel-surface.tsx"), "utf8");
  assert.match(panelSurface, /surface: \{ backgroundColor: tokens\.color\.surfaceMuted/);

  const searchField = await readFile(path.resolve(process.cwd(), "src/components/ui/search-field.tsx"), "utf8");
  assert.match(searchField, /field: \{[^}]*backgroundColor: tokens\.color\.surfaceMuted/);
  assert.match(searchField, /bleed && layoutStyles\.cardContentBleed/);

  for (const relativePath of ["src/components/libraries/library-list-screen.tsx", "src/components/pickers/composition-picker-screen.tsx", "src/app/program/activate.tsx"]) {
    const source = await readFile(path.resolve(process.cwd(), relativePath), "utf8");
    assert.match(source, /<SearchField/);
  }

  const mealAdherence = await readFile(path.resolve(process.cwd(), "src/components/calendarization/meal-adherence-check-in.tsx"), "utf8");
  assert.match(mealAdherence, /noteInput: \{[^}]*backgroundColor: tokens\.color\.surfaceMuted/);
});
