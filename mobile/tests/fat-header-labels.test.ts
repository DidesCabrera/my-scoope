import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { readTestFile } from "./support/source-contract";

test("fat panel headers and comparison legends use G for grasas", async () => {
  const files = [
    "src/components/panels/entity-panels.tsx",
    "src/components/calendarization/calendar-upcoming-panels.tsx",
    "src/components/libraries/program-day-comparison-panels.tsx",
    "src/components/libraries/program-week-comparison-panels.tsx",
    "src/components/comparisons/comparison-result.tsx",
    "src/sharing/presentation.ts",
  ];
  for (const file of files) {
    const source = await readTestFile(path.resolve(process.cwd(), file), "utf8");
    assert.doesNotMatch(source, /P\|C\|F|label: "F(?:g|%)?"|>F(?:%)?(?: <\/Text>|<\/Text>)|"F%"/);
  }

  const panels = await readTestFile(path.resolve(process.cwd(), files[0]!), "utf8");
  assert.match(panels, /\["C", "G"\]/);
  assert.match(panels, /\["P%", "C%", "G%"\]/);
  assert.match(panels, />P\|C\|G<\/PanelHeaderCell>/);
});
