import assert from "node:assert/strict";
import test from "node:test";

import { nextHeaderIdentityVisibility } from "../src/components/navigation/header-scroll";

test("compact header stays stable while fast scrolling crosses its threshold", () => {
  let visible = false;
  for (const [offset, expected] of [[0, false], [12, false], [17, false], [13, false], [19, true], [12, true], [7, true]] as const) {
    visible = nextHeaderIdentityVisibility(offset, visible);
    assert.equal(visible, expected);
  }
  assert.equal(nextHeaderIdentityVisibility(6, visible), false);
  assert.equal(nextHeaderIdentityVisibility(Number.NaN, true), true);
});
