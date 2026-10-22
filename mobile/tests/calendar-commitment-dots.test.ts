import assert from "node:assert/strict";
import test from "node:test";

import { commitmentDotKinds } from "../src/components/calendarization/calendar-commitment-dots";

test("calendar dots show every kind once, including a draft shopping day", () => {
  assert.deepEqual(commitmentDotKinds([{ kind: "cooking" }, { kind: "training" }], "shopping"), ["cooking", "training", "shopping"]);
  assert.deepEqual(commitmentDotKinds([{ kind: "shopping" }], "shopping"), ["shopping"]);
  assert.deepEqual(commitmentDotKinds(undefined), []);
});
