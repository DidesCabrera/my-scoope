import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("the mobile comparator preserves web slot and metric comparison dynamics", async () => {
  const screen = await readFile(path.resolve(process.cwd(), "src/app/comparator/index.tsx"), "utf8");
  const result = await readFile(path.resolve(process.cwd(), "src/components/comparisons/comparison-result.tsx"), "utf8");

  assert.match(screen, /function emptySlots\(\)/);
  assert.match(screen, /addSlot/);
  assert.match(screen, /removeSlot/);
  assert.match(screen, /slots\.flatMap/);
  assert.doesNotMatch(screen, /accessibilityRole="checkbox"/);
  assert.match(result, /result\.metrics\.map/);
  assert.match(result, /metric\.bars\.map/);
  assert.match(result, /relative_percentage/);
});
