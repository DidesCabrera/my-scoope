import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { PersonalPreparation } from "@/api/preparations";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { PreparationLibraryCard } from "@/components/preparations/preparation-library-card";
import { Button, InlineNotice, LoadingState, Screen, SearchField, SectionPageHeader } from "@/components/ui";
import { tokens } from "@/design/tokens";

const PAGE_SIZE = 30;
type PreparationPage = { items: PersonalPreparation[]; total: number; offset: number; limit: number };

export function ExplorePreparationsScreen() {
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [page, setPage] = useState<PreparationPage | null>(null);
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
      const result = await apiRequest<PreparationPage>(`/api/v1/explore/preparations?${params.toString()}`);
      setPage((current) => offset > 0 && current ? { ...result, items: [...current.items, ...result.items] } : result);
    } catch (failure) {
      setError(userFacingError(failure));
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [apiRequest, submittedQuery]);

  useFocusEffect(useCallback(() => {
    if (status === "authenticated") void load();
  }, [load, status]));

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/libraries/preparations" as Href, identityVisible: compactHeaderVisible, mode: "back", title: "Explorar preparaciones" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !page) return <LoadingState label="Cargando preparaciones globales…" />;

  return <Screen
    headerMode="preserve"
    onHeaderVisibilityChange={setCompactHeaderVisible}
    scrollHeader={<SectionPageHeader count={page?.total} countLabel="preparaciones globales" section="explore" subtitle="Consulta las preparaciones disponibles en el catálogo de My Scoope." title="Explorar preparaciones" />}
    stickyHeader={<SearchField accessibilityLabel="Buscar preparaciones globales" autoCapitalize="none" autoCorrect={false} onChangeText={setQuery} onClear={() => { setQuery(""); setSubmittedQuery(""); }} onSubmitEditing={() => setSubmittedQuery(query.trim())} placeholder="Buscar por nombre" returnKeyType="search" value={query} />}
    stickyHeaderStyle={styles.stickyHeader}>
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    {loading ? <LoadingState label="Actualizando resultados…" mode="content" /> : null}
    {!loading && page?.items.length === 0 ? <View style={styles.empty}><Text style={styles.emptyTitle}>No encontramos preparaciones</Text><Text style={styles.emptyCopy}>Prueba con otro nombre.</Text></View> : null}
    {!loading ? page?.items.map((item) => <PreparationLibraryCard item={item} key={item.id} onOpen={() => router.push(`/libraries/preparations/${item.id}` as Href)} />) : null}
    {!loading && page && page.items.length < page.total ? <Button label="Cargar más preparaciones" loading={loadingMore} onPress={() => void load(page.items.length)} variant="secondary" /> : null}
  </Screen>;
}

const styles = StyleSheet.create({
  empty: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderStyle: "dashed", borderWidth: 1, gap: tokens.spacing.sm, padding: tokens.spacing.xxl },
  emptyCopy: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20, textAlign: "center" },
  emptyTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.bold },
  stickyHeader: { paddingTop: tokens.spacing.sm },
});
