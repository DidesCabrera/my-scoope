import assert from "node:assert/strict";
import test from "node:test";

import { DEFAULT_MEAL_TIME, initialMealTime, isValidMealTime } from "../src/components/calendarization/meal-time";

test("meal time selector defaults to midnight when a meal has no saved hour", () => {
  assert.equal(DEFAULT_MEAL_TIME, "00:00");
  assert.equal(initialMealTime(null), "00:00");
  assert.equal(initialMealTime(""), "00:00");
  assert.equal(initialMealTime("invalid"), "00:00");
});

test("meal time selector preserves a valid saved hour", () => {
  assert.equal(initialMealTime("13:25:00"), "13:25");
  assert.equal(isValidMealTime("13:25"), true);
});
