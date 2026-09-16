import { useState } from "react";

export type PanelSortDirection = "asc" | "desc";

export type PanelSortState<Key extends string> = {
  direction: PanelSortDirection;
  key: Key;
} | null;

export type PanelSortValue = boolean | number | string | null | undefined;

export function nextPanelSort<Key extends string>(current: PanelSortState<Key>, key: Key): PanelSortState<Key> {
  if (!current || current.key !== key) return { direction: "desc", key };
  if (current.direction === "desc") return { direction: "asc", key };
  return null;
}

function comparePanelValues(left: PanelSortValue, right: PanelSortValue): number {
  if (left == null && right == null) return 0;
  if (left == null) return 1;
  if (right == null) return -1;
  if (typeof left === "number" && typeof right === "number") return left - right;
  if (typeof left === "boolean" && typeof right === "boolean") return Number(left) - Number(right);
  return String(left).localeCompare(String(right), "es-CL", { numeric: true, sensitivity: "base" });
}

export function sortPanelItems<T, Key extends string>(
  items: T[],
  sort: PanelSortState<Key>,
  values: Record<Key, (item: T) => PanelSortValue>,
): T[] {
  if (!sort) return items;
  return items
    .map((item, originalIndex) => ({ item, originalIndex }))
    .sort((left, right) => {
      const comparison = comparePanelValues(values[sort.key](left.item), values[sort.key](right.item));
      return comparison === 0 ? left.originalIndex - right.originalIndex : comparison * (sort.direction === "desc" ? -1 : 1);
    })
    .map(({ item }) => item);
}

export function useTemporaryPanelSort<T, Key extends string>(items: T[], values: Record<Key, (item: T) => PanelSortValue>) {
  const [sort, setSort] = useState<PanelSortState<Key>>(null);
  return {
    items: sortPanelItems(items, sort, values),
    onSort: (key: Key) => setSort((current) => nextPanelSort(current, key)),
    sort,
  };
}
