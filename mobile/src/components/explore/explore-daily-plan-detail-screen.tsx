import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";

import { userFacingError } from "@/api/errors";
import type { ExploreDailyPlanItem, ExploreDailyPlanSaveResult } from "@/api/explore-types";
import { useSession } from "@/auth/session-context";
import { LibraryCard } from "@/components/libraries/library-card";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { Button, InlineNotice, LoadingState, MutationStatusModal, Screen, SectionPageHeader, useMutationStatus } from "@/components/ui";

export function ExploreDailyPlanDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [item, setItem] = useState<ExploreDailyPlanItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const { clearStatus, runWithStatus, status: mutationStatus } = useMutationStatus();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItem(await apiRequest<ExploreDailyPlanItem>(`/api/v1/explore/daily-plans/${id}`));
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
    setHeaderPresentation({ fallback: "/explore/daily-plans" as Href, identityVisible: compactHeaderVisible, mode: "back", title: item?.name ?? "Explorar minuta" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, item?.name, setHeaderPresentation]));

  const saveToLibrary = async () => {
    if (!item || item.is_saved || saving) return;
    setSaving(true);
    setError(null);
    try {
      await runWithStatus(
        () => apiRequest<ExploreDailyPlanSaveResult>(`/api/v1/explore/daily-plans/${item.catalog_id}/save`, { method: "POST" }),
        { loadingLabel: "Guardando minuta", successLabel: "Minuta guardada" },
      );
      setItem((current) => current ? { ...current, is_saved: true } : current);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSaving(false);
    }
  };

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !item) return <LoadingState label="Abriendo minuta…" />;

  return (
    <>
      <Screen headerMode="preserve" onHeaderVisibilityChange={setCompactHeaderVisible}>
        <SectionPageHeader countLabel="minuta" section="explore" subtitle="Revisa sus comidas y guárdala como una copia editable en tu biblioteca." title={item?.name ?? "Explorar minuta"} />
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        {item ? <LibraryCard apiRequest={apiRequest} interactive={false} item={item} navigable={false} onChanged={() => undefined} onSaveToLibrary={saveToLibrary} savedToLibrary={item.is_saved} savingToLibrary={saving} /> : null}
        {item?.is_saved ? <Button label="Abrir Mis Minutas" onPress={() => router.push("/libraries/daily-plans" as Href)} variant="secondary" /> : null}
      </Screen>
      <MutationStatusModal onFinished={clearStatus} status={mutationStatus} />
    </>
  );
}
