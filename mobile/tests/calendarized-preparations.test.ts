import assert from "node:assert/strict";
import test from "node:test";

import type { MealSnapshot } from "../src/api/types";
import { snapshotDailyPlanFoodPanelItems, snapshotFoodPanelItems } from "../src/components/calendarization/presentation-adapters";

test("calendarized meal and daily-plan panels preserve preparation identity", () => {
  const meal: MealSnapshot = {
    foods: [
      { key: "prep-1", component_type: "preparation", source_preparation_id: 7, name: "Salsa", quantity_g: 100, protein_g: 4 },
      { key: "food-1", component_type: "food", source_food_id: 7, name: "Tomate", quantity_g: 50, protein_g: 1 },
    ],
    totals: { protein_g: 5, protein_per_kilogram: 0.1 },
  };

  assert.deepEqual(snapshotFoodPanelItems(meal).map(({ kind, detailId }) => [kind, detailId]), [
    ["preparation", 7],
    ["food", 7],
  ]);
  assert.deepEqual(snapshotDailyPlanFoodPanelItems([meal]).map(({ kind, detailId, quantity }) => [kind, detailId, quantity]), [
    ["preparation", 7, 100],
    ["food", 7, 50],
  ]);
});
