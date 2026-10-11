import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { foodNutritionFactRows, formatFoodNutrient } from "../src/components/details/food-nutrition-facts";

test("food nutrients distinguish measured zero from missing information", () => {
  assert.equal(formatFoodNutrient(0, "g"), "0 g");
  assert.equal(formatFoodNutrient(null, "g"), "Sin información");
  assert.equal(formatFoodNutrient(125.5, "mg"), "125,5 mg");
});

test("food nutrition facts use the approved icon-free key-value table", async () => {
  const [card, detail] = await Promise.all([
    readFile(path.resolve(process.cwd(), "src/components/details/food-nutrition-facts-card.tsx"), "utf8"),
    readFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8"),
  ]);
  const rows = foodNutritionFactRows({
    saturated_fat_g: 1.2,
    sugar_g: null,
    fiber_g: 0,
    sodium_mg: 125.5,
  });

  assert.deepEqual(rows.map(({ label }) => label), ["Grasas saturadas", "Azúcares", "Fibra", "Sodio"]);
  assert.deepEqual(rows.map(({ value }) => value), ["1,2 g", "Sin información", "0 g", "125,5 mg"]);
  assert.match(card, /<Card>/);
  assert.match(card, /<CardHeader density="compact"/);
  assert.match(card, /<KeyValueTable items=\{foodNutritionFactRows\(nutrition\)\}/);
  assert.doesNotMatch(card, /icon:/);
  assert.match(detail, /item\.entity === "food" && item\.food_nutrition/);
  assert.match(detail, /<FoodNutritionFactsCard nutrition=\{item\.food_nutrition\} quantityUnit=\{item\.quantity_unit \?\? "g"\}/);
});
