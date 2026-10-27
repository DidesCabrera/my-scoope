import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";

import { userFacingError } from "@/api/errors";
import type { ExploreMealItem, ExploreMealSaveResult } from "@/api/explore-types";
import { useSession } from "@/auth/session-context";
import { LibraryCard } from "@/components/libraries/library-card";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { Button, InlineNotice, LoadingState, MutationStatusModal, Screen, SectionPageHeader, useMutationStatus } from "@/components/ui";

export function ExploreMealDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [item, setItem] = useState<ExploreMealItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const { clearStatus, runWithStatus, status: mutationStatus } = useMutationStatus();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItem(await apiRequest<ExploreMealItem>(`/api/v1/explore/meals/${id}`));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, id]);

  useFocusEffect(useCallback(() => {
    if (status === "authenticated") void load();
  }, [load, status]));

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/explore/meals" as Href, identityVisible: compactHeaderVisible, mode: "back", title: item?.name ?? "Explorar comida" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, item?.name, setHeaderPresentation]));

  const saveToLibrary = async () => {
    if (!item || item.is_saved || saving) return;
    setSaving(true);
    setError(null);
    try {
      await runWithStatus(
        () => apiRequest<ExploreMealSaveResult>(`/api/v1/explore/meals/${item.catalog_id}/save`, { method: "POST" }),
        { loadingLabel: "Guardando comida", successLabel: "Comida guardada" },
      );
      setItem((current) => current ? { ...current, is_saved: true } : current);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSaving(false);
    }
  };

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !item) return <LoadingState label="Abriendo comida…" />;

  return (
    <>
      <Screen headerMode="preserve" onHeaderVisibilityChange={setCompactHeaderVisible}>
        <SectionPageHeader countLabel="comida" section="explore" subtitle="Revisa sus alimentos y guárdala como una copia editable en tu biblioteca." title={item?.name ?? "Explorar comida"} />
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        {item ? <LibraryCard apiRequest={apiRequest} interactive={false} item={item} navigable={false} onChanged={() => undefined} onSaveToLibrary={saveToLibrary} savedToLibrary={item.is_saved} savingToLibrary={saving} /> : null}
        {item?.is_saved ? <Button label="Abrir Mis Comidas" onPress={() => router.push("/libraries/meals" as Href)} variant="secondary" /> : null}
      </Screen>
      <MutationStatusModal onFinished={clearStatus} status={mutationStatus} />
    </>
  );
}

