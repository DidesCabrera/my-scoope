import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("all ellipsis action sheets enter from and dismiss toward the bottom", async () => {
  for (const file of [
    "src/components/libraries/library-actions.tsx",
    "src/components/libraries/context-card-actions.tsx",
    "src/components/libraries/library-list-actions.tsx",
    "src/components/programs/program-active-actions.tsx",
  ]) {
    const source = await readFile(path.resolve(process.cwd(), file), "utf8");
    assert.match(source, /<ActionSheetModal/);
    assert.doesNotMatch(source, /<Modal animationType=/);
  }

  const animation = await readFile(path.resolve(process.cwd(), "src/components/ui/action-sheet-modal.tsx"), "utf8");
  assert.match(animation, /animationType="none"/);
  assert.match(animation, /Animated\.timing\(scrimOpacity/);
  assert.match(animation, /Animated\.timing\(sheetTranslateY/);
  assert.match(animation, /toValue: hiddenSheetOffset/);
  assert.match(animation, /toValue: 0/);
  assert.match(animation, /useNativeDriver: true/);
  assert.match(animation, /paddingBottom: bottomInset/);
  assert.match(animation, /backgroundColor: tokens\.color\.surfaceCard/);
  assert.match(animation, /sheetFrame: \{[^}]*flexShrink: 1[^}]*maxHeight: "92%"/);
});

test("action sheets with forms scroll instead of clipping their final action", async () => {
  for (const file of [
    "src/components/calendarization/calendarized-entity-actions.tsx",
    "src/components/libraries/context-card-actions.tsx",
    "src/components/assistant/assistant-chat-actions.tsx",
    "src/components/comparisons/saved-comparison-actions.tsx",
    "src/app/weight.tsx",
  ]) {
    const source = await readFile(path.resolve(process.cwd(), file), "utf8");
    assert.match(source, /<ScrollView/);
    assert.match(source, /flexShrink: 1/);
  }

  const calendarizedActions = await readFile(path.resolve(process.cwd(), "src/components/calendarization/calendarized-entity-actions.tsx"), "utf8");
  assert.doesNotMatch(calendarizedActions, /maxHeight: "88%"|overflow: "hidden"/);
});
