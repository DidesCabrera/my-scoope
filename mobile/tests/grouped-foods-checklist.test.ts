import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("accumulated food lists expose the shared check column in active and library surfaces", async () => {
  const groupedFoods = await readFile(path.resolve(process.cwd(), "src/components/panels/grouped-foods-card.tsx"), "utf8");
  assert.match(groupedFoods, /useState<Set<string>>/);
  assert.match(groupedFoods, /const checklist = preparation \?\?/);
  assert.match(groupedFoods, /<FoodPanels items=\{items\} preparation=\{checklist\} preparationFirst=\{preparationFirst\} showPreparationColumn/);

  const accumulatedListSurfaces = [
    "src/components/libraries/library-detail-screen.tsx",
    "src/components/libraries/program-detail-preview.tsx",
    "src/components/calendarization/calendarized-program-planning.tsx",
    "src/app/program/days/[id].tsx",
  ];
  for (const relativePath of accumulatedListSurfaces) {
    const source = await readFile(path.resolve(process.cwd(), relativePath), "utf8");
    assert.match(source, /<GroupedFoodsCard/);
  }
});

test("shopping and cooking commitment lists use the shared check column", async () => {
  for (const relativePath of [
    "src/app/calendar/commitments.tsx",
    "src/app/calendar/commitments/[id].tsx",
  ]) {
    const source = await readFile(path.resolve(process.cwd(), relativePath), "utf8");
    assert.ok(source.includes("<GroupedFoodsCard"));
    assert.ok(!source.includes("showChecklist={false}"));
    assert.match(source, /Alimentos para cocinar/);
  }
});

test("commitment food card calculates explicitly and attaches the list to one day", async () => {
  const source = await readFile(path.resolve(process.cwd(), "src/app/calendar/commitments.tsx"), "utf8");
  assert.ok(source.includes('label="Calcular lista de alimentos"'));
  assert.ok(source.includes('label="Limpiar selección"'));
  assert.ok(source.includes('showContents={Boolean(foodPreview)}'));
  assert.ok(source.includes('setFoodAttachments((current) => ({ ...current, [day]: { start, end } }))'));
  assert.ok(source.includes('food_attachments: selected.flatMap'));
  assert.ok(source.includes('key={`commitment-detail-${editingFoodDate}`}'));
  assert.ok(source.includes('indicator={<Chip'));
  assert.ok(!source.includes('label="Adjuntar lista al'));
});
