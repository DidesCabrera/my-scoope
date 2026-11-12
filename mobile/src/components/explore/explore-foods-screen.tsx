import { type Href, Redirect, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { LibraryPageData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { LibraryCard } from "@/components/libraries/library-card";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { Button, InlineNotice, LoadingState, Screen, SearchField, SectionPageHeader } from "@/components/ui";
import { tokens } from "@/design/tokens";

const PAGE_SIZE = 30;

export function ExploreFoodsScreen() {
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [page, setPage] = useState<LibraryPageData | null>(null);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);

  const load = useCallback(async (offset = 0) => {
    if (offset === 0) setLoading(true);
    else setLoadingMore(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
      if (submittedQuery) params.set("search", submittedQuery);
      const result = await apiRequest<LibraryPageData>(`/api/v1/explore/foods?${params.toString()}`);
      setPage((current) => offset > 0 && current ? { ...result, items: [...current.items, ...result.items] } : result);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [apiRequest, submittedQuery]);

  useFocusEffect(useCallback(() => {
    if (status === "authenticated") void load();
  }, [load, status]));

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/libraries/foods" as Href, identityVisible: compactHeaderVisible, mode: "back", title: "Explorar alimentos" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !page) return <LoadingState label="Cargando alimentos globales…" />;

  return (
    <Screen
      headerMode="preserve"
      onHeaderVisibilityChange={setCompactHeaderVisible}
      scrollHeader={<SectionPageHeader count={page?.total} countLabel="alimentos globales" section="explore" subtitle="Consulta los alimentos disponibles en el catálogo de My Scoope." title="Explorar alimentos" />}
      stickyHeader={<SearchField accessibilityLabel="Buscar alimentos globales" autoCapitalize="none" autoCorrect={false} onChangeText={setQuery} onClear={() => { setQuery(""); setSubmittedQuery(""); }} onSubmitEditing={() => setSubmittedQuery(query.trim())} placeholder="Buscar por nombre" returnKeyType="search" value={query} />}
      stickyHeaderStyle={styles.stickyHeader}>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {loading ? <LoadingState label="Actualizando resultados…" mode="content" /> : null}
      {!loading && page?.items.length === 0 ? <View style={styles.empty}><Text style={styles.emptyTitle}>No encontramos alimentos</Text><Text style={styles.emptyCopy}>Prueba con otro nombre.</Text></View> : null}
      {!loading ? page?.items.map((item) => <LibraryCard apiRequest={apiRequest} interactive={false} item={item} key={item.id} navigable onChanged={() => undefined} />) : null}
      {!loading && page && page.items.length < page.total ? <Button label="Cargar más alimentos" loading={loadingMore} onPress={() => void load(page.items.length)} variant="secondary" /> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  empty: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderStyle: "dashed", borderWidth: 1, gap: tokens.spacing.sm, padding: tokens.spacing.xxl },
  emptyCopy: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20, textAlign: "center" },
  emptyTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.bold },
  stickyHeader: { paddingTop: tokens.spacing.sm },
});
