import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import { nextPanelSort, sortPanelItems, type PanelSortState } from "../src/components/panels/temporary-panel-sort";
import { assertSourceMatch, readTestFile } from "./support/source-contract";

type Row = { id: string; name: string; value: number };
type Key = "name" | "value";

const rows: Row[] = [
  { id: "a", name: "Beta", value: 2 },
  { id: "b", name: "Alfa", value: 5 },
  { id: "c", name: "Gamma", value: 2 },
];
const values = { name: (row: Row) => row.name, value: (row: Row) => row.value };

test("panel sort cycles through descending, ascending, and original order", () => {
  let sort: PanelSortState<Key> = null;
  sort = nextPanelSort(sort, "value");
  assert.deepEqual(sortPanelItems(rows, sort, values).map(({ id }) => id), ["b", "a", "c"]);

  sort = nextPanelSort(sort, "value");
  assert.deepEqual(sortPanelItems(rows, sort, values).map(({ id }) => id), ["a", "c", "b"]);

  sort = nextPanelSort(sort, "value");
  assert.equal(sort, null);
  assert.equal(sortPanelItems(rows, sort, values), rows);
});

test("changing columns starts with descending order and keeps equal rows stable", () => {
  const sort = nextPanelSort<Key>({ direction: "asc", key: "value" }, "name");
  assert.deepEqual(sort, { direction: "desc", key: "name" });
  assert.deepEqual(sortPanelItems(rows, sort, values).map(({ id }) => id), ["c", "a", "b"]);
});

test("all read-only mobile table panels use temporary sortable headers", async () => {
  for (const relativePath of [
    "src/components/panels/entity-panels.tsx",
    "src/components/libraries/program-day-comparison-panels.tsx",
    "src/components/libraries/program-week-comparison-panels.tsx",
  ]) {
    const source = await readTestFile(path.resolve(process.cwd(), relativePath), "utf8");
    assertSourceMatch(source, /SortablePanelHeaderCell/);
    assertSourceMatch(source, /useTemporaryPanelSort/);
    assertSourceMatch(source, /sorting\.sort \? undefined : (?:editing|gestures)/);
  }
});
