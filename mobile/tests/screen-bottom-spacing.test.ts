import assert from "node:assert/strict";
import test from "node:test";

import { screenBottomSpacing, SCREEN_BOTTOM_SPACING } from "../src/components/ui/screen-bottom-spacing-values";

test("full screens keep 96 pt below their last item while the keyboard is closed", () => {
  assert.equal(SCREEN_BOTTOM_SPACING, 96);
  assert.equal(screenBottomSpacing(false, 0), 96);
  assert.equal(screenBottomSpacing(false, 34), 96);
});

test("keyboard reduces bottom spacing while preserving the device inset", () => {
  assert.equal(screenBottomSpacing(true, 0), 16);
  assert.equal(screenBottomSpacing(true, 34), 42);
  assert.equal(screenBottomSpacing(true, 50), 58);
});
