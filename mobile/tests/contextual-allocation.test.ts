import assert from "node:assert/strict";
import test from "node:test";

import type { LibraryFoodPanelItem, LibraryMealPanelItem, MealSnapshot } from "../src/api/types";
import {
  libraryDailyPlanFoodPanelItems,
  snapshotDailyPlanFoodPanelItems,
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

test("calendarized food panels prefer API PPK and retain the legacy snapshot fallback", () => {
  const meal: MealSnapshot = {
    foods: [
      { name: "Directo", protein_g: 10, protein_per_kilogram: 0.25 },
      { name: "Compatible", protein_g: 20 },
    ],
    totals: { protein_g: 40, protein_per_kilogram: 0.5 },
  };

  assert.deepEqual(
    snapshotFoodPanelItems(meal).map((food) => food.proteinPerKilogram),
    [0.25, 0.25],
  );
});

test("calendarized food panels retain and aggregate proposed household equivalents", () => {
  const meals: MealSnapshot[] = [
    {
      foods: [{
        detail_id: 7,
        name: "Avena",
        quantity_g: 80,
        quantity_unit: "g",
        portion_display_quantity: 0.5,
        portion_display_measure: "cup",
      }],
    },
    {
      foods: [{
        detail_id: 7,
        name: "Avena",
        quantity_g: 160,
        quantity_unit: "g",
        portion_display_quantity: 1,
        portion_display_measure: "cup",
      }],
    },
  ];

  assert.deepEqual(
    snapshotFoodPanelItems(meals[0]).map((food) => [food.portionDisplayQuantity, food.portionDisplayMeasure]),
    [[0.5, "cup"]],
  );
  assert.deepEqual(
    snapshotDailyPlanFoodPanelItems(meals).map((food) => [food.portionDisplayQuantity, food.portionDisplayMeasure]),
    [[1.5, "cup"]],
  );
});

test("program daily-plan cards reuse the detail aggregation for their foods panel", () => {
  function food(quantity: number, protein: number, carbs: number, fat: number, portion: number): LibraryFoodPanelItem {
    return {
      calorie_distribution: { carbs: 0, fat: 0, protein: 0 },
      calorie_share: 0,
      calories: protein * 4 + carbs * 4 + fat * 9,
      carbs_allocation: 0,
      carbs_grams: carbs,
      detail_id: 7,
      fat_allocation: 0,
      fat_grams: fat,
      id: `oats-${quantity}`,
      name: "Avena",
      portion_display_measure: "cup",
      portion_display_quantity: portion,
      protein_allocation: 0,
      protein_grams: protein,
      protein_per_kilogram: null,
      quantity,
      quantity_unit: "g",
      relation_id: null,
    };
  }
  function meal(id: string, item: LibraryFoodPanelItem, proteinPerKilogram: number): LibraryMealPanelItem {
    return {
      calorie_distribution: { carbs: 0, fat: 0, protein: 0 },
      calorie_share: 0,
      calories: item.calories,
      carbs_allocation: 0,
      carbs_grams: item.carbs_grams,
      detail_id: null,
      fat_allocation: 0,
      fat_grams: item.fat_grams,
      foods: [item],
      id,
      name: id,
      note: "",
      protein_allocation: 0,
      protein_grams: item.protein_grams,
      protein_per_kilogram: proteinPerKilogram,
      relation_id: null,
      time: null,
    };
  }

  const items = libraryDailyPlanFoodPanelItems([
    meal("breakfast", food(80, 10, 30, 5, 0.5), 0.125),
    meal("snack", food(160, 20, 60, 10, 1), 0.25),
  ]);

  assert.equal(items.length, 1);
  assert.deepEqual(
    [items[0].name, items[0].quantity, items[0].portionDisplayQuantity, items[0].portionDisplayMeasure],
    ["Avena", 240, 1.5, "cup"],
  );
  assert.deepEqual(
    [items[0].proteinGrams, items[0].carbsGrams, items[0].fatGrams, items[0].proteinPerKilogram],
    [30, 90, 15, 0.375],
  );
});
