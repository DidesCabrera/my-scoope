import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";

import { userFacingError } from "@/api/errors";
import type { SavedComparisonDetail } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { ComparisonResultCards } from "@/components/comparisons/comparison-result";
import { RecoverableErrorState } from "@/components/ui/screen-states";
import { AppHeader, Button, LoadingState, Screen } from "@/components/ui/primitives";

export default function SavedComparisonDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { status, apiRequest } = useSession();
  const [comparison, setComparison] = useState<SavedComparisonDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try { setComparison(await apiRequest<SavedComparisonDetail>(`/api/v1/comparisons/saved/${id}`)); }
    catch (nextError) { setError(userFacingError(nextError)); }
    finally { setLoading(false); }
  }, [apiRequest, id]);
  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !comparison) return <LoadingState label="Abriendo la comparación…" />;
  return (
    <Screen>
      <AppHeader eyebrow={comparison?.kind_label ?? "Comparación guardada"} title={comparison?.saved_comparison_name ?? "Comparación"} />
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {comparison ? <ComparisonResultCards result={comparison} /> : null}
      {comparison ? <Button label="Editar comparación" onPress={() => router.push({ pathname: "/comparator", params: { savedId: String(comparison.saved_comparison_id) } } as Href)} /> : null}
      {comparison ? <Button label="Usar en el Asistente" onPress={() => router.push({ pathname: "/assistant/new", params: { comparisonId: String(comparison.saved_comparison_id) } } as Href)} variant="secondary" /> : null}
      <Button label="Volver a guardadas" onPress={() => router.replace("/comparator/saved" as Href)} variant="secondary" />
    </Screen>
  );
}
