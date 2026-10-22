import type { LibraryItem, LibraryPageData } from "@/api/types";

export type LibraryDeletionState = {
  empty: boolean;
  page: LibraryPageData;
  selectedIds: Set<number>;
};

export function applyLibraryDeletion(
  page: LibraryPageData,
  selectedIds: ReadonlySet<number>,
  affectedIds: readonly number[],
): LibraryDeletionState {
  const affected = new Set(affectedIds);
  const items = page.items.filter(({ id }) => !affected.has(id));
  const removedCount = page.items.length - items.length;

  return {
    empty: items.length === 0,
    page: { ...page, items, total: Math.max(0, page.total - removedCount) },
    selectedIds: new Set([...selectedIds].filter((id) => !affected.has(id))),
  };
}

export function containsSameLibraryItems(current: readonly LibraryItem[], candidate: readonly LibraryItem[]): boolean {
  if (current.length !== candidate.length) return false;
  const currentIds = new Set(current.map(({ id }) => id));
  return candidate.every(({ id }) => currentIds.has(id));
}
