import assert from "node:assert/strict";
import test from "node:test";

import { portionGrams, scaleFoodNutrition } from "../src/components/pickers/food-portion-nutrition";

const baseNutrition = {
  calories: 200,
  protein: { allocation: 40, grams: 20, per_kilogram: null },
  carbs: { allocation: 40, grams: 20 },
  fat: { allocation: 20, grams: 10 },
};

test("food KPI values scale from their 100 gram nutritional base", () => {
  assert.deepEqual(scaleFoodNutrition(baseNutrition, "250"), {
    calories: 500,
    protein: { allocation: 40, grams: 50, per_kilogram: null },
    carbs: { allocation: 40, grams: 50 },
    fat: { allocation: 20, grams: 25 },
  });
});

test("food portion accepts locale decimal commas and clears KPI values for invalid portions", () => {
  assert.equal(portionGrams("125,5"), 125.5);
  assert.deepEqual(scaleFoodNutrition(baseNutrition, ""), {
    calories: 0,
    protein: { allocation: 0, grams: 0, per_kilogram: null },
    carbs: { allocation: 0, grams: 0 },
    fat: { allocation: 0, grams: 0 },
  });
});
