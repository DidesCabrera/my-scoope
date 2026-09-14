import assert from "node:assert/strict";
import test from "node:test";

import type { MealExecutionItem } from "../src/api/types";
import { normalizeMealExecution, normalizeMealExecutionItem } from "../src/components/calendarization/meal-execution";

const baseExecution = {
  last_event_id: null,
  meal_key: "meal-1",
  recorded_at: null,
  status: "planned",
} satisfies Omit<MealExecutionItem, "note" | "prepared_food_keys">;

test("missing meal execution data is treated as an empty collection", () => {
  assert.deepEqual(normalizeMealExecution(undefined), []);
  assert.deepEqual(normalizeMealExecution(null), []);
});

test("older API responses without note or prepared food keys are safe", () => {
  assert.deepEqual(normalizeMealExecutionItem(baseExecution), {
    ...baseExecution,
    note: "",
    prepared_food_keys: [],
  });
});

test("null and malformed optional values are normalized without losing valid keys", () => {
  const execution = normalizeMealExecutionItem({
    ...baseExecution,
    note: null,
    prepared_food_keys: ["food-1", null, 7, "food-2"],
  } as unknown as MealExecutionItem);

  assert.equal(execution.note, "");
  assert.deepEqual(execution.prepared_food_keys, ["food-1", "food-2"]);
  assert.equal(execution.prepared_food_keys.includes("food-1"), true);
});

test("valid meal execution values are preserved", () => {
  const execution = normalizeMealExecutionItem({
    ...baseExecution,
    note: "Listo",
    prepared_food_keys: ["food-1"],
  });

  assert.equal(execution.note, "Listo");
  assert.deepEqual(execution.prepared_food_keys, ["food-1"]);
});
