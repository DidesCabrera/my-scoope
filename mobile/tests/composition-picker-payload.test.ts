import assert from "node:assert/strict";
import test from "node:test";

import { buildCompositionPickerPayload } from "../src/components/pickers/composition-picker-payload";

const defaults = {
  dayNumbers: [1],
  hour: "08:00",
  note: "",
  quantity: "125",
  selectedId: 77,
  weekNumber: 1,
};

test("calendarized food replacements preserve the exact snapshot key", () => {
  assert.deepEqual(buildCompositionPickerPayload({
    ...defaults,
    kind: "food-to-calendarized-meal",
    relationKey: "source_meal_food:314",
  }), {
    food_id: 77,
    food_snapshot_key: "source_meal_food:314",
    quantity: 125,
  });
});

test("calendarized meal replacements preserve the exact snapshot key", () => {
  assert.deepEqual(buildCompositionPickerPayload({
    ...defaults,
    kind: "meal-to-calendarized-day",
    relationKey: "source_dailyplan_meal:159",
  }), {
    hour: "08:00",
    meal_id: 77,
    meal_snapshot_key: "source_dailyplan_meal:159",
    note: "",
  });
});

test("library food replacements keep both composition context identifiers", () => {
  assert.deepEqual(buildCompositionPickerPayload({
    ...defaults,
    contextDailyPlanId: 18,
    contextDailyPlanMealId: 22,
    kind: "food-to-meal",
    relationId: 91,
  }), {
    dailyplan_id: 18,
    dailyplan_meal_id: 22,
    food_id: 77,
    meal_food_id: 91,
    quantity: 125,
  });
});
