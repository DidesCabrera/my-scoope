import assert from "node:assert/strict";
import test from "node:test";

import { sortedWeightTrend } from "../src/components/ui/weight-trend-values";

test("weight trend orders valid measurements chronologically without mutating history", () => {
  const history = [
    { id: 3, measured_on: "2026-10-07", weight_kg: 84.2 },
    { id: 1, measured_on: "2026-10-01", weight_kg: 85.1 },
    { id: 2, measured_on: "2026-10-04", weight_kg: Number.NaN },
  ];

  assert.deepEqual(sortedWeightTrend(history).map((item) => item.id), [1, 3]);
  assert.deepEqual(history.map((item) => item.id), [3, 1, 2]);
});
