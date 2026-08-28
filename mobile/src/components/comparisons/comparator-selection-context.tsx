import type { PropsWithChildren } from "react";
import { createContext, useCallback, useContext, useMemo, useRef } from "react";

import type { ComparisonKind, ComparisonOption } from "@/api/types";

export type PendingComparatorSelection = {
  kind: ComparisonKind;
  option: ComparisonOption;
  slotKey: number;
};

type ComparatorSelectionContextValue = {
  consumeSelection(): PendingComparatorSelection | null;
  publishSelection(selection: PendingComparatorSelection): void;
};

const ComparatorSelectionContext = createContext<ComparatorSelectionContextValue | null>(null);

export function ComparatorSelectionProvider({ children }: PropsWithChildren) {
  const pendingSelection = useRef<PendingComparatorSelection | null>(null);
  const consumeSelection = useCallback(() => {
    const selection = pendingSelection.current;
    pendingSelection.current = null;
    return selection;
  }, []);
  const publishSelection = useCallback((selection: PendingComparatorSelection) => {
    pendingSelection.current = selection;
  }, []);
  const value = useMemo(() => ({ consumeSelection, publishSelection }), [consumeSelection, publishSelection]);

  return <ComparatorSelectionContext.Provider value={value}>{children}</ComparatorSelectionContext.Provider>;
}

export function useComparatorSelectionTransfer() {
  const context = useContext(ComparatorSelectionContext);
  if (!context) throw new Error("useComparatorSelectionTransfer must be used inside ComparatorSelectionProvider");
  return context;
}
