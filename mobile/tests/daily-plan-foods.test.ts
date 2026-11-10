import assert from "node:assert/strict";
import test from "node:test";

import type { LibraryFoodPanelItem, LibraryNutrition, LibraryPanel } from "../src/api/types";
import { dailyPlanFoodPanelItems } from "../src/components/libraries/daily-plan-foods";

const nutrition: LibraryNutrition = {
  calories: 600,
  protein: { grams: 60, allocation: 40, per_kilogram: 0.75 },
  carbs: { grams: 60, allocation: 40 },
  fat: { grams: 20, allocation: 30 },
};

function food(id: number, quantity: number, overrides: Partial<LibraryFoodPanelItem> = {}): LibraryFoodPanelItem {
  return {
    id: `meal-food:${id}:${quantity}`,
    relation_id: id,
    detail_id: id,
    name: `Alimento ${id}`,
    quantity,
    quantity_unit: "g",
    calories: quantity,
    calorie_share: 0,
    calorie_distribution: { protein: 0, carbs: 0, fat: 0 },
    protein_grams: quantity / 10,
    protein_per_kilogram: null,
    carbs_grams: quantity / 10,
    fat_grams: 0,
    protein_allocation: 0,
    carbs_allocation: 0,
    fat_allocation: 0,
    ...overrides,
  };
}

function panel(mealFoods: LibraryFoodPanelItem[][], aggregate: LibraryFoodPanelItem[] = []): LibraryPanel {
  return {
    kind: "meals",
    foods: aggregate,
    meals: mealFoods.map((foods, index) => ({ id: `meal:${index}`, foods } as LibraryPanel["meals"][number])),
    weeks: [],
  };
}

test("minuta card derives and aggregates food rows from its meals when panel.foods is empty", () => {
  const result = dailyPlanFoodPanelItems(panel([
    [food(1, 100, { portion_display_quantity: 1, portion_display_measure: "taza" }), food(2, 50)],
    [food(1, 80, { portion_display_quantity: 0.8, portion_display_measure: "taza" })],
  ]), nutrition);

  assert.equal(result.length, 2);
  assert.equal(result[0]?.quantity, 180);
  assert.equal(result[0]?.calories, 180);
  assert.equal(result[0]?.protein_grams, 18);
  assert.equal(result[0]?.portion_display_quantity, 1.8);
  assert.equal(result[0]?.calorie_share, 30);
  assert.equal(result[0]?.protein_allocation, 30);
  assert.equal(result[0]?.protein_per_kilogram, 0.225);
  assert.equal(result[0]?.relation_id, null);
  assert.notEqual(result[0]?.id, result[1]?.id);
});

test("minuta card uses the authoritative aggregate when available", () => {
  const aggregate = [food(3, 120)];
  assert.equal(dailyPlanFoodPanelItems(panel([[food(1, 80)]], aggregate), nutrition), aggregate);
});

test("empty minutas stay empty and incompatible portion measures are not combined", () => {
  assert.deepEqual(dailyPlanFoodPanelItems(panel([]), nutrition), []);
  const result = dailyPlanFoodPanelItems(panel([[
    food(1, 100, { portion_display_quantity: 1, portion_display_measure: "taza" }),
    food(1, 100, { portion_display_quantity: 1, portion_display_measure: "unidad" }),
  ]]), nutrition);
  assert.equal(result[0]?.portion_display_quantity, null);
  assert.equal(result[0]?.portion_display_measure, null);
});
