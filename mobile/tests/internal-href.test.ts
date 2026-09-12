import assert from "node:assert/strict";
import test from "node:test";

import { internalHref } from "../src/navigation/internal-href";

test("internalHref preserves local navigation destinations only", () => {
  assert.equal(internalHref("/program/days/42"), "/program/days/42");
  assert.equal(internalHref("/libraries/daily-plans/7?returnTo=%2Fprogram"), "/libraries/daily-plans/7?returnTo=%2Fprogram");
  assert.equal(internalHref(["/libraries/daily-plans/7"]), "/libraries/daily-plans/7");
  assert.equal(internalHref("https://example.com"), undefined);
  assert.equal(internalHref("//example.com/path"), undefined);
  assert.equal(internalHref("/program\\days\\42"), undefined);
  assert.equal(internalHref(undefined), undefined);
});
