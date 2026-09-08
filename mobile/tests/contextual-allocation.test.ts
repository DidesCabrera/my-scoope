import assert from "node:assert/strict";
import test from "node:test";

import type { MealSnapshot } from "../src/api/types";
import {
  snapshotFoodPanelItems,
  snapshotMacroDistribution,
  snapshotMealPanelItem,
} from "../src/components/calendarization/presentation-adapters";
import { contextualMacroAllocations } from "../src/components/panels/contextual-allocation";

test("Alloc expresses each row contribution to each macro in the visible context", () => {
  const allocations = contextualMacroAllocations([
    { proteinGrams: 30, carbsGrams: 10, fatGrams: 0 },
    { proteinGrams: 10, carbsGrams: 30, fatGrams: 20 },
  ]);

  assert.deepEqual(allocations, [
    { protein: 75, carbs: 25, fat: 0 },
    { protein: 25, carbs: 75, fat: 100 },
  ]);
});

test("Alloc returns zero for empty macro columns and invalid values", () => {
  assert.deepEqual(
    contextualMacroAllocations([
      { proteinGrams: Number.NaN, carbsGrams: 0, fatGrams: -2 },
      { proteinGrams: 0, carbsGrams: 0, fatGrams: 0 },
    ]),
    [
      { protein: 0, carbs: 0, fat: 0 },
      { protein: 0, carbs: 0, fat: 0 },
    ],
  );
});

test("calendarized panels keep macro distribution separate from contextual Alloc", () => {
  const breakfast: MealSnapshot = {
    key: "breakfast",
    name: "Desayuno",
    foods: [
      { key: "oats", name: "Avena", quantity_g: 100, protein_g: 10, carbs_g: 30, fat_g: 5 },
      { key: "yogurt", name: "Yogur", quantity_g: 100, protein_g: 30, carbs_g: 10, fat_g: 5 },
    ],
    totals: { protein_g: 40, carbs_g: 40, fat_g: 10 },
  };

  assert.equal(snapshotMacroDistribution(breakfast.totals, "protein_g"), 160 / 410 * 100);
  assert.deepEqual(
    snapshotFoodPanelItems(breakfast).map((food) => [food.proteinAllocation, food.carbsAllocation, food.fatAllocation]),
    [[25, 75, 50], [75, 25, 50]],
  );

  const meal = snapshotMealPanelItem(
    breakfast,
    0,
    { protein_g: 50, carbs_g: 80, fat_g: 20 },
  );
  assert.deepEqual(
    [meal.proteinAllocation, meal.carbsAllocation, meal.fatAllocation],
    [80, 50, 50],
  );
});
