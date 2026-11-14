import assert from "node:assert/strict";
import test from "node:test";

import type { PreparationDetail } from "../src/api/preparations";
import { preparationNutritionForGrams } from "../src/components/preparations/preparation-nutrition-basis";

const recipe = {
  yield_g: 200,
  nutrition: {
    calories: 400,
    protein_g: 20,
    protein_per_kilogram: 0.25,
    carbs_g: 50,
    fat_g: 10,
    sodium_mg: 300,
  },
} as PreparationDetail;

test("preparation nutrition follows the exact grams selected in a meal", () => {
  assert.deepEqual(preparationNutritionForGrams(recipe, 75), {
    calories: 150,
    protein_g: 7.5,
    protein_per_kilogram: 0.09375,
    carbs_g: 18.75,
    fat_g: 3.75,
    sodium_mg: 112.5,
  });
  assert.deepEqual(preparationNutritionForGrams(recipe, 100), {
    calories: 200,
    protein_g: 10,
    protein_per_kilogram: 0.125,
    carbs_g: 25,
    fat_g: 5,
    sodium_mg: 150,
  });
});

test("preparation nutrition retains unavailable optional metrics", () => {
  const withoutOptional = { ...recipe, nutrition: { ...recipe.nutrition, protein_per_kilogram: null, sodium_mg: null } };
  const portion = preparationNutritionForGrams(withoutOptional, 100);
  assert.equal(portion.protein_per_kilogram, null);
  assert.equal(portion.sodium_mg, null);
});
