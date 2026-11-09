import assert from "node:assert/strict";
import test from "node:test";

import type { PreparationDetail } from "../src/api/preparations";
import type { LibraryItem } from "../src/api/types";
import { projectPreparationMeal } from "../src/components/preparations/preparation-meal-preview";
import { ingredientPanelItem } from "../src/components/preparations/preparation-panel-items";

const meal = {
  name: "Almuerzo",
  nutrition: {
    calories: 440,
    protein: { grams: 15, allocation: 14, per_kilogram: 0.2 },
    carbs: { grams: 35, allocation: 32 },
    fat: { grams: 27, allocation: 54 },
  },
  panel: {
    kind: "foods",
    foods: [{
      id: "food:7", relation_id: 7, detail_id: 7, name: "Acelga cocida", quantity: 175,
      quantity_unit: "g", calories: 44, protein_grams: 3, protein_per_kilogram: null,
      carbs_grams: 7, fat_grams: 1,
    }],
    preparations: [{
      relation_id: 8, detail_id: 9, name: "Completo italiano", version: 1,
      quantity_g: 179, selected_units: 1, selection_mode: "units", household_label: "completo mediano",
      calories: 396, protein_g: 12, carbs_g: 28, fat_g: 26, sodium_mg: null, allergens: [], ingredients: [],
    }],
  },
} as unknown as LibraryItem;

const selected = {
  id: 9, name: "Completo italiano", version: 1, household_label: "completo mediano",
  default_portion_g: 179, yield_g: 179, selection_mode: "units", selected_units: 0.5, grams: 89.5,
  nutrition: { calories: 198, protein_g: 6, carbs_g: 14, fat_g: 13, sodium_mg: null },
  allergens: [], allergen_status: "", evidence: {}, ingredients: [],
} as PreparationDetail;

test("adding a preparation includes its selected portion in the meal total and panel", () => {
  const preview = projectPreparationMeal(meal, selected);
  assert.ok(preview);
  assert.equal(preview.nutrition.calories, 638);
  assert.equal(preview.nutrition.protein.grams, 21);
  assert.equal(preview.foodCount, 1);
  assert.equal(preview.preparationCount, 2);
  assert.equal(preview.items.length, 3);
  assert.equal(preview.items[2].quantity, 0.5);
  assert.equal(preview.items[2].projectedLabel, "Por agregar");
  assert.equal(preview.contribution.calories, 198);
  assert.equal(meal.nutrition.calories, 440);
});

test("editing a preparation replaces its former contribution instead of counting it twice", () => {
  const preview = projectPreparationMeal(meal, selected, 8);
  assert.ok(preview);
  assert.equal(preview.nutrition.calories, 242);
  assert.equal(preview.nutrition.protein.grams, 9);
  assert.equal(preview.preparationCount, 1);
  assert.equal(preview.items.length, 2);
  assert.equal(preview.items[1].quantity, 0.5);
  assert.equal(preview.items[1].projectedLabel, "Por actualizar");
  assert.equal(projectPreparationMeal(meal, selected, 999), null);
});

test("preparation components use meal-style rows without culinary-state badges", () => {
  const food = ingredientPanelItem({
    food_id: 12, name: "Pan de completo", quantity_g: 45, preparation_state: "ready_to_eat",
    is_condiment: false, calories: 120, protein_g: 4, carbs_g: 22, fat_g: 2,
  }, 0, selected);
  assert.equal(food.kind, "food");
  assert.equal(food.detailId, 12);
  assert.equal(food.projectedLabel, undefined);

  const nested = ingredientPanelItem({
    preparation_id: 22, name: "Salsa casera", quantity_g: 30,
    calories: 40, protein_g: 1, carbs_g: 3, fat_g: 3,
  }, 1, selected);
  assert.equal(nested.kind, "preparation");
  assert.equal(nested.detailId, 22);
  assert.equal(nested.projectedLabel, undefined);
});
