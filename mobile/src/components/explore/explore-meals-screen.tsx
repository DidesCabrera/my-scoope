import { type Href, Redirect, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ExploreMealDietaryStyle, ExploreMealItem, ExploreMealOccasion, ExploreMealPageData, ExploreMealSaveResult } from "@/api/explore-types";
import { useSession } from "@/auth/session-context";
import { LibraryCard } from "@/components/libraries/library-card";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { InlineNotice, LoadingState, MutationStatusModal, Screen, ScrollableTabBar, SearchField, SectionPageHeader, useMutationStatus } from "@/components/ui";
import { tokens } from "@/design/tokens";

type OccasionFilter = "all" | ExploreMealOccasion;
type DietaryFilter = "all" | ExploreMealDietaryStyle;

const occasionTabs: { key: OccasionFilter; label: string }[] = [
  { key: "all", label: "Todas" },
  { key: "breakfast", label: "Desayuno" },
  { key: "lunch", label: "Almuerzo" },
  { key: "dinner", label: "Cena" },
  { key: "snack", label: "Colación" },
  { key: "pre_workout", label: "Pre-entreno" },
  { key: "post_workout", label: "Post-entreno" },
];

const dietaryTabs: { key: DietaryFilter; label: string }[] = [
  { key: "all", label: "Todos los estilos" },
  { key: "omnivore", label: "Omnívoras" },
  { key: "pescatarian", label: "Pescetarianas" },
  { key: "vegetarian", label: "Vegetarianas" },
  { key: "vegan", label: "Veganas" },
];

export function ExploreMealsScreen() {
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [page, setPage] = useState<ExploreMealPageData | null>(null);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [occasion, setOccasion] = useState<OccasionFilter>("all");
  const [dietaryStyle, setDietaryStyle] = useState<DietaryFilter>("all");
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
      if (occasion !== "all") params.set("occasion", occasion);
      if (dietaryStyle !== "all") params.set("dietary_style", dietaryStyle);
      setPage(await apiRequest<ExploreMealPageData>(`/api/v1/explore/meals?${params.toString()}`));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, dietaryStyle, occasion, submittedQuery]);

  useFocusEffect(useCallback(() => {
    if (status === "authenticated") void load();
  }, [load, status]));

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/today" as Href, identityVisible: false, mode: "back", title: "Explorar comidas" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [setHeaderPresentation]));

  const saveToLibrary = async (item: ExploreMealItem) => {
    if (item.is_saved || savingCatalogId != null) return;
    setSavingCatalogId(item.catalog_id);
    setError(null);
    try {
      const result = await runWithStatus(
        () => apiRequest<ExploreMealSaveResult>(`/api/v1/explore/meals/${item.catalog_id}/save`, { method: "POST" }),
        { loadingLabel: "Guardando comida", successLabel: "Comida guardada" },
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
  if (loading && !page) return <LoadingState label="Preparando comidas para explorar…" />;

  return (
    <>
      <Screen
        headerMode="preserve"
        scrollHeader={<SectionPageHeader count={page?.total} countLabel="comidas disponibles" section="explore" subtitle="Comidas seleccionadas por My Scoope para distintas ocasiones y estilos de alimentación." title="Explorar comidas" />}
        stickyHeader={<View style={styles.filters}>
          <SearchField accessibilityLabel="Buscar comidas para explorar" autoCapitalize="none" autoCorrect={false} onChangeText={setQuery} onClear={() => { setQuery(""); setSubmittedQuery(""); }} onSubmitEditing={() => setSubmittedQuery(query.trim())} placeholder="Buscar por nombre o descripción" returnKeyType="search" value={query} />
          <ScrollableTabBar accessibilityLabel="Filtrar por ocasión" activeTab={occasion} density="compact" onChange={(tab) => setOccasion(tab as OccasionFilter)} tabs={occasionTabs} />
          <ScrollableTabBar accessibilityLabel="Filtrar por estilo alimentario" activeTab={dietaryStyle} density="compact" onChange={(tab) => setDietaryStyle(tab as DietaryFilter)} tabs={dietaryTabs} />
        </View>}
        stickyHeaderStyle={styles.stickyHeader}>
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        {loading ? <LoadingState label="Actualizando resultados…" mode="content" /> : null}
        {!loading && page?.items.length === 0 ? <View style={styles.empty}><Text style={styles.emptyTitle}>No encontramos comidas</Text><Text style={styles.emptyCopy}>Prueba con otra ocasión, estilo o búsqueda.</Text></View> : null}
        {!loading ? page?.items.map((item) => (
          <LibraryCard
            apiRequest={apiRequest}
            detailHref={`/explore/meals/${item.catalog_id}` as Href}
            interactive={false}
            item={item}
            key={item.catalog_id}
            navigable
            onChanged={() => undefined}
            onSaveToLibrary={() => saveToLibrary(item)}
            savedToLibrary={item.is_saved}
            savingToLibrary={savingCatalogId === item.catalog_id}
          />
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

