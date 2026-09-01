import type { SelectedComparisonOption } from "@/api/types";

export type ComparisonSlot = {
  key: number;
  option: SelectedComparisonOption | null;
  quantity: string;
};

export type ComparatorSelection = {
  slotKey: number;
  option: SelectedComparisonOption;
};

export function initialComparisonSlots(): ComparisonSlot[] {
  return [
    { key: 1, option: null, quantity: "100" },
    { key: 2, option: null, quantity: "100" },
  ];
}

export function applyComparatorSelection(
  slots: readonly ComparisonSlot[],
  selection: ComparatorSelection,
): ComparisonSlot[] {
  return slots.map((slot) =>
    slot.key === selection.slotKey ? { ...slot, option: selection.option } : slot,
  );
}
