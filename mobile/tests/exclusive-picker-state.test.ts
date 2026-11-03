import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { nextExclusivePicker } from "../src/components/ui/exclusive-picker-state";

test("opening a picker replaces the previously expanded picker", () => {
  assert.equal(nextExclusivePicker("height", "weight", true), "weight");
  assert.equal(nextExclusivePicker("weight", "height", true), "height");
});

test("closing a picker only clears that picker", () => {
  assert.equal(nextExclusivePicker("height", "height", false), null);
  assert.equal(nextExclusivePicker("weight", "height", false), "weight");
});

test("onboarding controls height and weight as one exclusive picker group", async () => {
  const [journey, measurementField] = await Promise.all([
    readFile(path.resolve(process.cwd(), "src/components/onboarding/onboarding-journey-view.tsx"), "utf8"),
    readFile(path.resolve(process.cwd(), "src/components/ui/native-measurement-field.native.tsx"), "utf8"),
  ]);

  assert.match(journey, /expanded=\{expandedMeasurement === "height"\}/);
  assert.match(journey, /expanded=\{expandedMeasurement === "weight"\}/);
  assert.match(journey, /nextExclusivePicker\(current, "height", expanded\)/);
  assert.match(journey, /nextExclusivePicker\(current, "weight", expanded\)/);
  assert.match(measurementField, /const visible = expanded \?\? internalExpanded/);
});
