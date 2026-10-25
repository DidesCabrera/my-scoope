import { type Href, Redirect, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ExploreDailyPlanItem, ExploreDailyPlanPageData, ExploreDailyPlanSaveResult, ExploreMealDietaryStyle } from "@/api/explore-types";
import { useSession } from "@/auth/session-context";
import { LibraryCard } from "@/components/libraries/library-card";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { InlineNotice, LoadingState, MutationStatusModal, Screen, ScrollableTabBar, SearchField, SectionPageHeader, useMutationStatus } from "@/components/ui";
import { tokens } from "@/design/tokens";

type DietaryFilter = "all" | ExploreMealDietaryStyle;
type CountFilter = "all" | "3" | "4";

const dietaryTabs: { key: DietaryFilter; label: string }[] = [
  { key: "all", label: "Todos los estilos" },
  { key: "omnivore", label: "Omnívoras" },
  { key: "pescatarian", label: "Pescetarianas" },
  { key: "vegetarian", label: "Vegetarianas" },
  { key: "vegan", label: "Veganas" },
];
const countTabs: { key: CountFilter; label: string }[] = [
  { key: "all", label: "Todas las cantidades" },
  { key: "3", label: "3 comidas" },
  { key: "4", label: "4 comidas" },
];

export function ExploreDailyPlansScreen() {
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [page, setPage] = useState<ExploreDailyPlanPageData | null>(null);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [dietaryStyle, setDietaryStyle] = useState<DietaryFilter>("all");
  const [mealCount, setMealCount] = useState<CountFilter>("all");
  const [savingCatalogId, setSavingCatalogId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { clearStatus, runWithStatus, status: mutationStatus } = useMutationStatus();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: "100", offset: "0" });
      if (submittedQuery) params.set("search", submittedQuery);
      if (dietaryStyle !== "all") params.set("dietary_style", dietaryStyle);
      if (mealCount !== "all") params.set("meal_count", mealCount);
      setPage(await apiRequest<ExploreDailyPlanPageData>(`/api/v1/explore/daily-plans?${params.toString()}`));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, dietaryStyle, mealCount, submittedQuery]);

  useFocusEffect(useCallback(() => {
    if (status === "authenticated") void load();
  }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/libraries/daily-plans" as Href, identityVisible: false, mode: "back", title: "Explorar minutas" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [setHeaderPresentation]));

  const saveToLibrary = async (item: ExploreDailyPlanItem) => {
    if (item.is_saved || savingCatalogId != null) return;
    setSavingCatalogId(item.catalog_id);
    setError(null);
    try {
      const result = await runWithStatus(
        () => apiRequest<ExploreDailyPlanSaveResult>(`/api/v1/explore/daily-plans/${item.catalog_id}/save`, { method: "POST" }),
        { loadingLabel: "Guardando minuta", successLabel: "Minuta guardada" },
      );
      setPage((current) => current ? {
        ...current,
        items: current.items.map((candidate) => candidate.catalog_id === item.catalog_id ? { ...candidate, is_saved: true } : candidate),
      } : current);
      if (result.already_saved) clearStatus();
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSavingCatalogId(null);
    }
  };

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !page) return <LoadingState label="Preparando minutas para explorar…" />;

  return (
    <>
      <Screen
        headerMode="preserve"
        scrollHeader={<SectionPageHeader count={page?.total} countLabel="minutas disponibles" section="explore" subtitle="Minutas diarias seleccionadas por My Scoope para distintos estilos y cantidades de comidas." title="Explorar minutas" />}
        stickyHeader={<View style={styles.filters}>
          <SearchField accessibilityLabel="Buscar minutas para explorar" autoCapitalize="none" autoCorrect={false} onChangeText={setQuery} onClear={() => { setQuery(""); setSubmittedQuery(""); }} onSubmitEditing={() => setSubmittedQuery(query.trim())} placeholder="Buscar por nombre o descripción" returnKeyType="search" value={query} />
          <ScrollableTabBar accessibilityLabel="Filtrar por estilo alimentario" activeTab={dietaryStyle} density="compact" onChange={(tab) => setDietaryStyle(tab as DietaryFilter)} tabs={dietaryTabs} />
          <ScrollableTabBar accessibilityLabel="Filtrar por cantidad de comidas" activeTab={mealCount} density="compact" onChange={(tab) => setMealCount(tab as CountFilter)} tabs={countTabs} />
        </View>}
        stickyHeaderStyle={styles.stickyHeader}>
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        {loading ? <LoadingState label="Actualizando resultados…" mode="content" /> : null}
        {!loading && page?.items.length === 0 ? <View style={styles.empty}><Text style={styles.emptyTitle}>No encontramos minutas</Text><Text style={styles.emptyCopy}>Prueba con otro estilo, cantidad de comidas o búsqueda.</Text></View> : null}
        {!loading ? page?.items.map((item) => (
          <LibraryCard apiRequest={apiRequest} detailHref={`/explore/daily-plans/${item.catalog_id}` as Href} interactive={false} item={item} key={item.catalog_id} navigable onChanged={() => undefined} onSaveToLibrary={() => saveToLibrary(item)} savedToLibrary={item.is_saved} savingToLibrary={savingCatalogId === item.catalog_id} />
        )) : null}
      </Screen>
      <MutationStatusModal onFinished={clearStatus} status={mutationStatus} />
    </>
  );
}

const styles = StyleSheet.create({
  empty: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderStyle: "dashed", borderWidth: 1, gap: tokens.spacing.sm, padding: tokens.spacing.xxl },
  emptyCopy: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20, textAlign: "center" },
  emptyTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.bold },
  filters: { gap: tokens.spacing.sm },
  stickyHeader: { gap: 0, paddingTop: tokens.spacing.sm },
});
