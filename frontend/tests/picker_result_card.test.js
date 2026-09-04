import assert from "node:assert/strict";
import test from "node:test";

import {
  projectDailyPlanResultItems,
  projectMealResultItems,
  withResultMetrics,
} from "../../notas/static/notas/js/picker_result_card.js";

test("projectMealResultItems includes the selected food in the resulting Meal", () => {
  const items = projectMealResultItems(
    [{
      mealfood_id: 4,
      food_id: 10,
      name: "Arroz",
      quantity: 150,
      protein: 4,
      carbs: 42,
      fat: 1,
      total_kcal: 193,
    }],
    { id: 11, name: "Pollo", protein: 30, carbs: 0, fat: 5, total_kcal: 165 },
    120,
  );

  assert.equal(items.length, 2);
  assert.equal(items[0].foodId, 10);
  assert.equal(items[1].foodId, 11);
  assert.equal(items[1].protein, 36);
  assert.equal(items[1].total_kcal, 198);
  assert.equal(items[1].projectedLabel, "Por agregar");
});

test("projectMealResultItems replaces the edited relation in the projection", () => {
  const items = projectMealResultItems(
    [
      { mealfood_id: 4, name: "Arroz", quantity: 150, protein: 4, carbs: 42, fat: 1, total_kcal: 193 },
      { mealfood_id: 5, name: "Atún", quantity: 80, protein: 20, carbs: 0, fat: 1, total_kcal: 89 },
    ],
    { display_name: "Salmón", protein: 22, carbs: 0, fat: 12, total_kcal: 196 },
    90,
    5,
  );

  assert.equal(items.length, 2);
  assert.equal(items[1].name, "Salmón");
  assert.equal(items[1].projectedLabel, "Reemplazo");
});

test("projectDailyPlanResultItems includes schedule metadata and replaces edited slot", () => {
  const items = projectDailyPlanResultItems(
    [
      { dailyplanmeal_id: 8, name: "Desayuno", hour: "08:00", note: "", protein: 20, carbs: 30, fat: 8, total_kcal: 272, foods: [] },
      { dailyplanmeal_id: 9, name: "Almuerzo", hour: "13:00", note: "Trabajo", protein: 35, carbs: 60, fat: 15, total_kcal: 515, foods: [] },
    ],
    { id: 12, name: "Cena", protein: 30, carbs: 20, fat: 10, total_kcal: 290, foods: [{ id: 3, name: "Salmón" }] },
    {
      hour: "20:30",
      note: "Después de entrenar",
      editingDailyPlanMealId: 9,
    },
  );

  assert.equal(items.length, 2);
  assert.equal(items[0].name, "Desayuno");
  assert.equal(items[1].name, "Cena");
  assert.equal(items[1].hour, "20:30");
  assert.equal(items[1].note, "Después de entrenar");
  assert.equal(items[1].foods[0].name, "Salmón");
  assert.equal(items[1].projectedLabel, "Reemplazo");
});

test("withResultMetrics recalculates table shares against the projected entity", () => {
  const rows = withResultMetrics(
    [
      { name: "Base", protein: 10, carbs: 20, fat: 5, total_kcal: 165 },
      { name: "Nuevo", protein: 10, carbs: 0, fat: 5, total_kcal: 85 },
    ],
    { protein: 20, carbs: 20, fat: 10, total_kcal: 250 },
  );

  assert.equal(rows[0].kcalShare, 66);
  assert.equal(rows[1].kcalShare, 34);
  assert.equal(rows[0].alloc.protein, 50);
  assert.equal(rows[1].alloc.fat, 50);
});

test("projected Food allocation changes when its quantity changes", () => {
  const existing = [{
    mealfood_id: 4,
    food_id: 10,
    name: "Arroz",
    quantity: 100,
    protein: 5,
    carbs: 40,
    fat: 0,
    total_kcal: 180,
  }];
  const selected = {
    id: 11,
    name: "Pollo",
    protein: 25,
    carbs: 0,
    fat: 5,
    total_kcal: 145,
  };

  const rowsAt100 = withResultMetrics(
    projectMealResultItems(existing, selected, 100),
    { protein: 30, carbs: 40, fat: 5, total_kcal: 325 },
  );
  const rowsAt200 = withResultMetrics(
    projectMealResultItems(existing, selected, 200),
    { protein: 55, carbs: 40, fat: 10, total_kcal: 470 },
  );

  assert.ok(rowsAt200[1].alloc.protein > rowsAt100[1].alloc.protein);
  assert.ok(rowsAt200[1].kcalShare > rowsAt100[1].kcalShare);
});
