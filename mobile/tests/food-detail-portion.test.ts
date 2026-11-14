import assert from "node:assert/strict";
import test from "node:test";

import { foodNutritionForPortion } from "../src/components/libraries/presentation-adapters";

test("food portion scales KPI quantities while retaining macro percentages", () => {
  const per100 = {
    calories: 63,
    protein: { grams: 3, allocation: 19, per_kilogram: 0.04 },
    carbs: { grams: 12, allocation: 77 },
    fat: { grams: 0, allocation: 5 },
  };
  const portion = foodNutritionForPortion(per100, 150);
  assert.equal(portion.calories, 94.5);
  assert.equal(portion.protein.grams, 4.5);
  assert.equal(portion.protein.per_kilogram, 0.06);
  assert.equal(portion.carbs.grams, 18);
  assert.equal(portion.fat.grams, 0);
  assert.equal(portion.protein.allocation, 19);
  assert.equal(portion.carbs.allocation, 77);
  assert.deepEqual(per100, {
    calories: 63,
    protein: { grams: 3, allocation: 19, per_kilogram: 0.04 },
    carbs: { grams: 12, allocation: 77 },
    fat: { grams: 0, allocation: 5 },
  });
});

test("food portion preserves missing protein per kilogram", () => {
  const portion = foodNutritionForPortion({
    calories: 200,
    protein: { grams: 10, allocation: 20, per_kilogram: null },
    carbs: { grams: 20, allocation: 40 },
    fat: { grams: 10, allocation: 40 },
  }, 50);
  assert.equal(portion.calories, 100);
  assert.equal(portion.protein.per_kilogram, null);
});
