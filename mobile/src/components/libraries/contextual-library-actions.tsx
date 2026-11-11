import { type Href, useRouter } from "expo-router";
import type { ReactNode } from "react";

import type { LibraryAction, LibraryActionResult, LibraryEntity, LibraryItem } from "@/api/types";
import { useComparatorSelectionTransfer } from "@/components/comparisons/comparator-selection-context";

import { LibraryActions } from "./library-actions";

type ApiRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

const entityConfig = {
  dailyPlan: { comparisonKind: "dailyplans", slug: "daily-plans" },
  meal: { comparisonKind: "meals", slug: "meals" },
} as const;

export function ContextualLibraryActions({ apiRequest, entity, id, name, onChanged, onRemove, onRemoveFromCalendar, onRenameCalendarized, onReplace, onReplacePlan, movePlan, calendarActionsDisabled, sourceActionsDisabled, onOpenInformation, onVisibleChange, renderTrigger, visible }: {
  apiRequest: ApiRequest;
  entity: Extract<LibraryEntity, "dailyPlan" | "meal">;
  id?: number;
  name: string;
  onChanged(): Promise<void> | void;
  onRemove?: () => Promise<void>;
  onRemoveFromCalendar?: () => Promise<void>;
  onRenameCalendarized?: (name: string) => Promise<void>;
  onReplace?: () => void;
  onReplacePlan?: () => void;
  movePlan?: { sourceDate: string; localToday: string; disabled?: boolean; onMoved(): Promise<void> | void };
  calendarActionsDisabled?: boolean;
  sourceActionsDisabled?: boolean;
  onOpenInformation?: () => void;
  onVisibleChange?: (visible: boolean) => void;
  renderTrigger?: (open: () => void) => ReactNode;
  visible?: boolean;
}) {
  const router = useRouter();
  const { publishSelection } = useComparatorSelectionTransfer();
  const config = entityConfig[entity];
  const actions: LibraryAction[] = id == null ? [] : [
    { destructive: false, key: "share", label: "Compartir" },
    { destructive: false, key: "rename", label: "Renombrar" },
  ];
  if (id == null && onRenameCalendarized) actions.push({ destructive: false, key: "rename", label: "Renombrar" });
  if (id != null && !onRemoveFromCalendar && !onRemove) {
    actions.push({ destructive: true, key: "delete", label: "Eliminar" });
  }

  const compare = async () => {
    if (id == null) return;
    const item = await apiRequest<LibraryItem>(`/api/v1/library/${config.slug}/${id}`);
    publishSelection({ kind: config.comparisonKind, option: item, slotKey: 1 });
    router.push({ pathname: "/comparator", params: { create: "1", kind: config.comparisonKind } } as Href);
  };

  return (
    <LibraryActions
      apiRequest={apiRequest}
      entitySlug={config.slug}
      item={{
        actions,
        entity,
        id: id ?? 0,
        name,
      }}
      onCompare={id != null ? () => void compare() : undefined}
      onCompleted={(_result: LibraryActionResult) => void onChanged()}
      onRemoveFromCalendar={onRemoveFromCalendar}
      onRenameCalendarized={onRenameCalendarized}
      onRemove={onRemove}
      onReplace={onReplace}
      onReplacePlan={onReplacePlan}
      movePlan={movePlan}
      calendarActionsDisabled={calendarActionsDisabled}
      sourceActionsDisabled={sourceActionsDisabled}
      onOpenInformation={onOpenInformation}
      onVisibleChange={onVisibleChange}
      renderTrigger={renderTrigger}
      visible={visible}
      removeContext={onRemove ? "calendarizedDay" : undefined}
    />
  );
}
