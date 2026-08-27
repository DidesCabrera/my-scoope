import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("card action sheets enter from and dismiss toward the bottom", async () => {
  for (const file of ["library-actions.tsx", "context-card-actions.tsx"]) {
    const source = await readFile(path.resolve(process.cwd(), "src/components/libraries", file), "utf8");
    assert.match(source, /<ActionSheetModal/);
    assert.doesNotMatch(source, /<Modal animationType=/);
  }

  const animation = await readFile(path.resolve(process.cwd(), "src/components/libraries/action-sheet-modal.tsx"), "utf8");
  assert.match(animation, /animationType="none"/);
  assert.match(animation, /Animated\.timing\(scrimOpacity/);
  assert.match(animation, /Animated\.timing\(sheetTranslateY/);
  assert.match(animation, /toValue: hiddenSheetOffset/);
  assert.match(animation, /toValue: 0/);
  assert.match(animation, /useNativeDriver: true/);
});
