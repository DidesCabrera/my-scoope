import assert from "node:assert/strict";
import test from "node:test";

import { macroCalorieShares } from "../src/components/nutrition/macro-calorie-shares";

test("macro calorie shares use the 4/4/9 energy contract and total 100", () => {
  const shares = macroCalorieShares({ proteinGrams: 31, carbsGrams: 0, fatGrams: 3.6 });
  assert.deepEqual(shares, { protein: 79, carbs: 0, fat: 21 });
  assert.equal(shares.protein + shares.carbs + shares.fat, 100);
});

test("macro calorie shares handle empty and invalid values safely", () => {
  assert.deepEqual(macroCalorieShares({ proteinGrams: 0, carbsGrams: 0, fatGrams: 0 }), { protein: 0, carbs: 0, fat: 0 });
  assert.deepEqual(macroCalorieShares({ proteinGrams: Number.NaN, carbsGrams: -4, fatGrams: 2 }), { protein: 0, carbs: 0, fat: 100 });
});
