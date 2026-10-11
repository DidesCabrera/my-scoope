import assert from "node:assert/strict";
import test from "node:test";

import { foodNutritionFactRows, formatFoodNutrient } from "../src/components/details/food-nutrition-facts";

test("food nutrients distinguish measured zero from missing information", () => {
  assert.equal(formatFoodNutrient(0, "g"), "0 g");
  assert.equal(formatFoodNutrient(null, "g"), "Sin información");
  assert.equal(formatFoodNutrient(125.5, "mg"), "125,5 mg");
});

test("food nutrition facts expose the approved rows in display order", () => {
  const rows = foodNutritionFactRows({
    saturated_fat_g: 1.2,
    sugar_g: null,
    fiber_g: 0,
    sodium_mg: 125.5,
  });

  assert.deepEqual(rows.map(({ label }) => label), ["Grasas saturadas", "Azúcares", "Fibra", "Sodio"]);
  assert.deepEqual(rows.map(({ value }) => value), ["1,2 g", "Sin información", "0 g", "125,5 mg"]);
});
