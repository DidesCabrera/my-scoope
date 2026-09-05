import assert from "node:assert/strict";
import test from "node:test";

import {
  applyComparatorSelection,
  initialComparisonSlots,
} from "../src/components/comparisons/comparison-state";

test("comparison builder starts with two independent empty slots", () => {
  const slots = initialComparisonSlots();

  assert.deepEqual(slots, [
    { key: 1, option: null, quantity: "100" },
    { key: 2, option: null, quantity: "100" },
  ]);
  assert.notEqual(slots[0], slots[1]);
});

test("picker result updates only its destination without mutating prior state", () => {
  const original = initialComparisonSlots();
  const option = { id: 42, name: "Avena" };

  const updated = applyComparatorSelection(original, { slotKey: 2, option });

  assert.equal(original[1]?.option, null);
  assert.equal(updated[0], original[0]);
  assert.deepEqual(updated[1], { key: 2, option, quantity: "100" });
});

test("stale picker result leaves slots unchanged", () => {
  const original = initialComparisonSlots();

  const updated = applyComparatorSelection(original, {
    slotKey: 999,
    option: { id: 7, name: "Arroz" },
  });

  assert.deepEqual(updated, original);
});
