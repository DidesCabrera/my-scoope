import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string) {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("UI System exposes intrinsic scrollable and full-width distributed tab bars", async () => {
  const tabs = await source("src/components/ui/tab-bars.tsx");
  const exports = await source("src/components/ui/index.ts");

  assert.match(exports, /export \* from "\.\/tab-bars"/);
  assert.match(tabs, /export function ScrollableTabBar/);
  assert.match(tabs, /<ScrollView[\s\S]*horizontal[\s\S]*showsHorizontalScrollIndicator=\{false\}/);
  assert.match(tabs, /scrollableTab: \{[^}]*flexDirection: "row"/);
  assert.doesNotMatch(tabs, /scrollableTab: \{[^}]*flex: 1/);
  assert.match(tabs, /density\?: "compact" \| "regular"/);
  assert.match(tabs, /scrollableTabCompact: \{[^}]*minHeight: 30/);
  assert.match(tabs, /export function DistributedTabBar/);
  assert.match(tabs, /distributedBar: \{[^}]*width: "100%"/);
  assert.match(tabs, /distributedTab: \{[^}]*flex: 1/);
  assert.match(tabs, /distributedTab: \{[^}]*justifyContent: "center"/);
  assert.match(tabs, /tab\.count != null/);
});

test("domain tab bars use the matching UI System layout contract", async () => {
  const assistant = await source("src/components/assistant/assistant-section-tabs.tsx");
  const comparator = await source("src/components/comparisons/comparison-components.tsx");
  const picker = await source("src/components/pickers/picker-entry-tabs.tsx");
  const weeks = await source("src/components/libraries/program-planning-controls.tsx");

  assert.match(assistant, /<DistributedTabBar<AssistantSection>/);
  assert.match(picker, /<DistributedTabBar<PickerEntryTab>/);
  assert.match(comparator, /<ScrollableTabBar/);
  assert.match(weeks, /<ScrollableTabBar[\s\S]*density="compact"/);
});
