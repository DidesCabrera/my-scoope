import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(file: string): Promise<string> {
  return readFile(path.resolve(process.cwd(), file), "utf8");
}

test("all ellipsis action sheets enter from and dismiss toward the bottom", async () => {
  for (const file of [
    "src/components/libraries/library-actions.tsx",
    "src/components/libraries/context-card-actions.tsx",
    "src/components/libraries/library-list-actions.tsx",
    "src/components/programs/program-active-actions.tsx",
  ]) {
    const contents = await source(file);
    assert.match(contents, /<ActionSheetModal/);
    assert.doesNotMatch(contents, /<Modal animationType=/);
  }

  const animation = await source("src/components/ui/action-sheet-modal.tsx");
  assert.match(animation, /animationType="none"/);
  assert.match(animation, /Animated\.timing\(scrimOpacity/);
  assert.match(animation, /Animated\.timing\(sheetTranslateY/);
  assert.match(animation, /toValue: hiddenSheetOffset/);
  assert.match(animation, /toValue: 0/);
  assert.match(animation, /useNativeDriver: true/);
  assert.match(animation, /paddingBottom: bottomInset/);
  assert.match(animation, /backgroundColor: tokens\.color\.surfaceCard/);
  assert.equal(animation.includes('flexShrink: 1, maxHeight: "92%"'), true);
});

test("action sheets with forms scroll instead of clipping their final action", async () => {
  for (const file of [
    "src/components/calendarization/calendarized-entity-actions.tsx",
    "src/components/libraries/context-card-actions.tsx",
    "src/components/assistant/assistant-chat-actions.tsx",
    "src/components/comparisons/saved-comparison-actions.tsx",
    "src/app/weight.tsx",
  ]) {
    const contents = await source(file);
    assert.equal(contents.includes("<ScrollView"), true);
    assert.equal(contents.includes("flexShrink: 1"), true);
  }

  const calendarizedActions = await source("src/components/calendarization/calendarized-entity-actions.tsx");
  assert.equal(calendarizedActions.includes('maxHeight: "88%"'), false);
  assert.equal(calendarizedActions.includes('overflow: "hidden"'), false);
});
