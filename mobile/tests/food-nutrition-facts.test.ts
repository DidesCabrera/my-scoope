import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { formatNutritionFact, formatNutritionFactForPortion, formatNutritionPortion, nutritionFactRows } from "../src/components/ui/nutrition-facts";
import { assertSourceDoesNotMatch, assertSourceMatch, readTestFile } from "./support/source-contract";

test("food nutrients distinguish measured zero from missing information", () => {
  assert.equal(formatNutritionFact(0, "g"), "0 g");
  assert.equal(formatNutritionFact(null, "g"), "-");
  assert.equal(formatNutritionFact(125.5, "mg"), "125,5 mg");
});

test("nutrition portions use the registered quantity without inventing missing data", () => {
  assert.equal(formatNutritionPortion(30, "g"), "30 g");
  assert.equal(formatNutritionPortion(125.5, "ml"), "125,5 ml");
  assert.equal(formatNutritionPortion(null, "g"), "-");
  assert.equal(formatNutritionFactForPortion(79, 30, "g"), "23,7 g");
  assert.equal(formatNutritionFactForPortion(0, 30, "g"), "0 g");
  assert.equal(formatNutritionFactForPortion(79, null, "g"), "-");
});

test("nutrition facts use the registered portion as the third column header", async () => {
  const card = await readTestFile(path.resolve(process.cwd(), "src/components/ui/nutrition-facts-card.tsx"), "utf8");
  assertSourceMatch(card, /\{formatNutritionPortion\(portion\.quantity, portion\.unit\)\}<\/Text>/);
  assertSourceDoesNotMatch(card, />PORCIÓN<\/Text>/);
  assertSourceMatch(card, /card: \{ marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding, paddingBottom:/);
  assertSourceMatch(card, /table: \{ marginHorizontal: tokens\.layout\.reducedInset - tokens\.card\.outerPadding \}/);
  assertSourceDoesNotMatch(card, /(?:card|table): \{[^}]*marginTop: -/);
});

test("food nutrition facts expose the approved rows in display order", () => {
  const rows = nutritionFactRows({
    proteinG: 79,
    totalFatG: 4,
    saturatedFatG: 1.2,
    carbsG: 6,
    sugarG: null,
    fiberG: 0,
    sodiumMg: 125.5,
  }, 30);

  assert.deepEqual(rows.map(({ label }) => label), ["Proteínas", "Grasas totales", "Grasas saturadas", "Carbohidratos", "Azúcares", "Fibra", "Sodio"]);
  assert.deepEqual(rows.map(({ per100Value }) => per100Value), ["79 g", "4 g", "1,2 g", "6 g", "-", "0 g", "125,5 mg"]);
  assert.deepEqual(rows.map(({ portionValue }) => portionValue), ["23,7 g", "1,2 g", "0,4 g", "1,8 g", "-", "0 g", "37,7 mg"]);
  assert.deepEqual(rows.map(({ emphasized }) => emphasized), [true, true, false, true, false, false, false]);
});
