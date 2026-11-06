import assert from "node:assert/strict";
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
