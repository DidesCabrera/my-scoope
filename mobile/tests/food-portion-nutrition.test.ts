import assert from "node:assert/strict";
import test from "node:test";

import {
  convertFoodPortionAmount,
  defaultFoodPortionSelection,
  foodPortionMetricAmount,
  portionGrams,
  restoredFoodPortionSelection,
  scaleFoodNutrition,
} from "../src/components/pickers/food-portion-nutrition";

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

test("household measures convert the selected amount to the metric nutrition quantity", () => {
  const egg = { defaultPortion: 65, householdAmount: 1, householdMeasure: "unit", householdMeasureLabel: "unidad" };
  assert.equal(foodPortionMetricAmount("2", "household", egg), 130);
  assert.equal(foodPortionMetricAmount("65", "metric", egg), 65);

  const oats = { defaultPortion: 40, householdAmount: 0.5, householdMeasure: "cup", householdMeasureLabel: "taza" };
  assert.equal(foodPortionMetricAmount("1", "household", oats), 80);
});

test("new foods prefer the proposed household measure and fall back to the metric unit", () => {
  assert.deepEqual(defaultFoodPortionSelection({ defaultPortion: 65, householdAmount: 1, householdMeasure: "unit", householdMeasureLabel: "unidad" }), {
    measure: "household",
    quantity: "1",
  });
  assert.deepEqual(defaultFoodPortionSelection({ defaultPortion: 30, householdAmount: null, householdMeasure: "", householdMeasureLabel: "" }), {
    measure: "metric",
    quantity: "30",
  });
});

test("changing the measure preserves the real portion and editing restores the chosen household value", () => {
  const egg = { defaultPortion: 65, householdAmount: 1, householdMeasure: "unit", householdMeasureLabel: "unidad" };
  assert.equal(convertFoodPortionAmount("2", "household", "metric", egg), "130");
  assert.equal(convertFoodPortionAmount("130", "metric", "household", egg), "2");
  assert.deepEqual(restoredFoodPortionSelection(130, 2, "unit", egg), { measure: "household", quantity: "2" });
  assert.deepEqual(restoredFoodPortionSelection(130, 130, "g", egg), { measure: "metric", quantity: "130" });
});
