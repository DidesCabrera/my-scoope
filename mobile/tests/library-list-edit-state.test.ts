import assert from "node:assert/strict";
import test from "node:test";

import type { LibraryItem, LibraryPageData } from "../src/api/types";
import { applyLibraryDeletion, containsSameLibraryItems } from "../src/components/libraries/library-list-edit-state";

function item(id: number): LibraryItem {
  return { entity: "meal", id, name: `Meal ${id}` } as LibraryItem;
}

test("library deletion removes affected items and selected IDs as one state transition", () => {
  const page = { items: [item(1), item(2), item(3)], limit: 3, offset: 0, search: null, total: 3 } as LibraryPageData;

  const next = applyLibraryDeletion(page, new Set([1, 2, 3]), [1, 3]);

  assert.deepEqual(next.page.items.map(({ id }) => id), [2]);
  assert.deepEqual([...next.selectedIds], [2]);
  assert.equal(next.page.total, 1);
  assert.equal(next.empty, false);
});

test("library deletion reports an empty editor so the screen can leave edit mode", () => {
  const page = { items: [item(7)], limit: 1, offset: 0, search: null, total: 1 } as LibraryPageData;

  const next = applyLibraryDeletion(page, new Set([7]), [7]);

  assert.equal(next.empty, true);
  assert.equal(next.page.total, 0);
  assert.deepEqual(next.page.items, []);
  assert.deepEqual([...next.selectedIds], []);
});

test("stale reorder callbacks cannot restore an item deleted from the editor", () => {
  const current = [item(1), item(2)];

  assert.equal(containsSameLibraryItems(current, [item(2), item(1)]), true);
  assert.equal(containsSameLibraryItems(current, [item(3), item(2), item(1)]), false);
  assert.equal(containsSameLibraryItems(current, [item(2)]), false);
});
