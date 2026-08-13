import { Redirect, useFocusEffect } from "expo-router";
import { Search, X } from "lucide-react-native";
import { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { LibraryEntity, LibraryPageData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { Button, Card, InlineNotice, textStyles } from "@/components/ui/primitives";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { tokens } from "@/design/tokens";

import { LibraryCard } from "./library-card";
import { CollectionPageHeader } from "./entity-card";

type LibraryListScreenProps = {
  emptyDescription: string;
  endpoint: string;
  entity: LibraryEntity;
  title: string;
};

export function LibraryListScreen({ emptyDescription, endpoint, entity, title }: LibraryListScreenProps) {
  const { status, apiRequest } = useSession();
  const [page, setPage] = useState<LibraryPageData | null>(null);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setHeaderPresentation = useHeaderPresentation();
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ mode: "library-list", entity, identityVisible: compactHeaderVisible, title });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, entity, setHeaderPresentation, title]));

  const load = useCallback(async ({ append = false, offset = 0, refresh = false } = {}) => {
    if (refresh) setRefreshing(true);
    else if (append) setLoadingMore(true);
    else setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        limit: "30",
        offset: append ? String(offset) : "0",
      });
      if (submittedQuery) params.set("search", submittedQuery);
      const nextPage = await apiRequest<LibraryPageData>(`${endpoint}?${params.toString()}`);
      setPage((current) => append && current ? { ...nextPage, items: [...current.items, ...nextPage.items] } : nextPage);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
      setLoadingMore(false);
      setRefreshing(false);
    }
  }, [apiRequest, endpoint, submittedQuery]);

  useFocusEffect(useCallback(() => {
    void load();
  }, [load]));

  if (status === "anonymous") return <Redirect href="/login" />;

  return (
    <ScrollView
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
      onScroll={({ nativeEvent }) => {
        const visible = nativeEvent.contentOffset.y > 1;
        if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible);
      }}
      refreshControl={<RefreshControl onRefresh={() => void load({ refresh: true })} refreshing={refreshing} tintColor={tokens.color.interactivePrimary} />}
      scrollEventThrottle={16}
      style={styles.screen}>
      <CollectionPageHeader count={page?.total} countIcon={entity === "program" ? "week" : entity === "dailyPlan" ? "meal" : entity === "meal" ? "food" : "food"} entity={entity} title={title} />
      <View style={styles.searchField}>
        <Search color={tokens.color.textSoft} size={20} />
        <TextInput
          accessibilityLabel={`Buscar en ${title}`}
          autoCapitalize="none"
          autoCorrect={false}
          onChangeText={setQuery}
          onSubmitEditing={() => setSubmittedQuery(query.trim())}
          placeholder="Buscar por nombre"
          placeholderTextColor={tokens.color.textSubtle}
          returnKeyType="search"
          style={styles.searchInput}
          value={query}
        />
        {query ? (
          <Pressable
            accessibilityLabel="Limpiar búsqueda"
            onPress={() => {
              setQuery("");
              setSubmittedQuery("");
            }}
            style={styles.clearButton}>
            <X color={tokens.color.textMuted} size={18} />
          </Pressable>
        ) : null}
      </View>
      {error ? (
        <Card>
          <InlineNotice tone="error">{error}</InlineNotice>
          <Button label="Reintentar" onPress={() => void load()} variant="secondary" />
        </Card>
      ) : null}
      {loading && !page ? (
        <View style={styles.loading}>
          <ActivityIndicator color={tokens.color.interactivePrimary} size="large" />
          <Text style={textStyles.muted}>Cargando tu librería…</Text>
        </View>
      ) : null}
      {!loading && page?.items.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={[styles.emptySymbol, { color: tokens.color[entity] }]}>＋</Text>
          <Text style={styles.emptyTitle}>{submittedQuery ? "Sin resultados" : `Aún no tienes ${title.toLowerCase()}`}</Text>
          <Text style={styles.emptyDescription}>{submittedQuery ? "Prueba con otra búsqueda." : emptyDescription}</Text>
        </View>
      ) : null}
      {page?.items.map((item) => <LibraryCard item={item} key={`${item.entity}-${item.id}`} />)}
      {page && page.items.length < page.total ? (
        <Button
          label={`Cargar más (${page.total - page.items.length})`}
          loading={loadingMore}
          onPress={() => void load({ append: true, offset: page.items.length })}
          variant="secondary"
        />
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  content: { flexGrow: 1, gap: tokens.spacing.lg, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  searchField: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.lg, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, minHeight: 52, paddingHorizontal: tokens.spacing.md },
  searchInput: { color: tokens.color.textMain, flex: 1, fontSize: 16, minHeight: 50, paddingVertical: 0 },
  clearButton: { alignItems: "center", height: 40, justifyContent: "center", width: 36 },
  loading: { alignItems: "center", flex: 1, gap: tokens.spacing.md, justifyContent: "center", minHeight: 240 },
  emptyState: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderStyle: "dashed", borderWidth: 1, gap: tokens.spacing.sm, padding: tokens.spacing.xxl },
  emptySymbol: { fontSize: tokens.type.hero, fontWeight: "300" },
  emptyTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800", textAlign: "center" },
  emptyDescription: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23, textAlign: "center" },
});
