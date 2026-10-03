import { type Href, Redirect, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";

import { userFacingError } from "@/api/errors";
import type { LibraryItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { EntityDetailMetadata } from "@/components/details";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { LoadingState, Screen } from "@/components/ui";
import { RecoverableErrorState } from "@/components/ui/screen-states";

import { libraryDate } from "./presentation-adapters";

type LibraryEntitySlug = "foods" | "meals" | "daily-plans" | "programs";

export function LibraryItemInformationScreen({ entitySlug }: { entitySlug: LibraryEntitySlug }) {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [item, setItem] = useState<LibraryItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setItem(await apiRequest<LibraryItem>(`/api/v1/library/${entitySlug}/${id}`));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, entitySlug, id]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: `/libraries/${entitySlug}/${id}` as Href, mode: "back", title: "Información del elemento" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [entitySlug, id, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !item) return <LoadingState label="Abriendo la información…" />;

  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {item ? <EntityDetailMetadata creator={item.creator} updatedAt={libraryDate(item.created_at)} /> : null}
    </Screen>
  );
}
