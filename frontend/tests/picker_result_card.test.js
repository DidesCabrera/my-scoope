import assert from "node:assert/strict";
import test from "node:test";

import {
  projectDailyPlanResultItems,
  projectMealResultItems,
} from "../../notas/static/notas/js/picker_result_card.js";

test("projectMealResultItems includes the selected food in the resulting Meal", () => {
  const items = projectMealResultItems(
    [{ mealfood_id: 4, name: "Arroz", quantity: 150 }],
    { name: "Pollo" },
    120,
  );

  assert.deepEqual(items, [
    { name: "Arroz", meta: "150 g|ml" },
    {
      name: "Pollo",
      meta: "120 g|ml",
      isProjected: true,
      projectedLabel: "Por agregar",
    },
  ]);
});

test("projectMealResultItems replaces the edited relation in the projection", () => {
  const items = projectMealResultItems(
    [
      { mealfood_id: 4, name: "Arroz", quantity: 150 },
      { mealfood_id: 5, name: "Atún", quantity: 80 },
    ],
    { display_name: "Salmón" },
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
      { dailyplanmeal_id: 8, name: "Desayuno", hour: "08:00", note: "" },
      { dailyplanmeal_id: 9, name: "Almuerzo", hour: "13:00", note: "Trabajo" },
    ],
    { name: "Cena" },
    {
      hour: "20:30",
      note: "Después de entrenar",
      editingDailyPlanMealId: 9,
    },
  );

  assert.deepEqual(items, [
    { name: "Desayuno", meta: "08:00" },
    {
      name: "Cena",
      meta: "20:30 · Después de entrenar",
      isProjected: true,
      projectedLabel: "Reemplazo",
    },
  ]);
});
