import { type Href, useRouter } from "expo-router";

import type { LibraryActionResult, LibraryEntity, LibraryItem } from "@/api/types";
import { useComparatorSelectionTransfer } from "@/components/comparisons/comparator-selection-context";

import { LibraryActions } from "./library-actions";

type ApiRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

const entityConfig = {
  dailyPlan: { comparisonKind: "dailyplans", slug: "daily-plans" },
  meal: { comparisonKind: "meals", slug: "meals" },
} as const;

export function ContextualLibraryActions({ apiRequest, entity, id, name, onChanged }: {
  apiRequest: ApiRequest;
  entity: Extract<LibraryEntity, "dailyPlan" | "meal">;
  id: number;
  name: string;
  onChanged(): Promise<void> | void;
}) {
  const router = useRouter();
  const { publishSelection } = useComparatorSelectionTransfer();
  const config = entityConfig[entity];

  const compare = async () => {
    const item = await apiRequest<LibraryItem>(`/api/v1/library/${config.slug}/${id}`);
    publishSelection({ kind: config.comparisonKind, option: item, slotKey: 1 });
    router.push({ pathname: "/comparator", params: { create: "1", kind: config.comparisonKind } } as Href);
  };

  return (
    <LibraryActions
      apiRequest={apiRequest}
      entitySlug={config.slug}
      item={{
        actions: [
          { destructive: false, key: "rename", label: "Renombrar" },
          { destructive: false, key: "share", label: "Compartir" },
          { destructive: true, key: "delete", label: "Eliminar" },
        ],
        entity,
        id,
        name,
      }}
      onCompare={() => void compare()}
      onCompleted={(_result: LibraryActionResult) => void onChanged()}
    />
  );
}
