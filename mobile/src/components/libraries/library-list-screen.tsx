import { Redirect, useFocusEffect, useRouter } from "expo-router";
import { Check, ChevronDown, ChevronUp, Search, Square, X } from "lucide-react-native";
import { useCallback, useRef, useState } from "react";
import { ActivityIndicator, Alert, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { LibraryEntity, LibraryPageData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { Button, Card, InlineNotice, textStyles } from "@/components/ui/primitives";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { tokens } from "@/design/tokens";

import { LibraryCard } from "./library-card";
import { LibraryListActions } from "./library-list-actions";
import { CollectionPageHeader } from "@/components/ui";

type LibraryListScreenProps = {
  emptyDescription: string;
  endpoint: string;
  entity: LibraryEntity;
  title: string;
};

const createLabels: Record<LibraryEntity, string> = {
  food: "+ Crear alimento",
  meal: "+ Crear comida",
  dailyPlan: "+ Crear plan diario",
  program: "+ Crear programa",
};

export function LibraryListScreen({ emptyDescription, endpoint, entity, title }: LibraryListScreenProps) {
  const { status, apiRequest } = useSession();
  const router = useRouter();
  const [page, setPage] = useState<LibraryPageData | null>(null);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setHeaderPresentation = useHeaderPresentation();
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [searchPinned, setSearchPinned] = useState(false);
  const searchOffset = useRef(Number.POSITIVE_INFINITY);
  const [actionsVisible, setActionsVisible] = useState(false);
  const [mode, setMode] = useState<"list" | "reorder" | "delete">("list");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [submitting, setSubmitting] = useState(false);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ mode: "library-list", action: { label: `Acciones de ${title}`, onPress: () => setActionsVisible(true) }, borderVisible: !searchPinned, entity, identityVisible: compactHeaderVisible, title });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, entity, searchPinned, setHeaderPresentation, title]));

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
      if (entity === "meal" || entity === "dailyPlan") params.set("include_drafts", "true");
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
  }, [apiRequest, endpoint, entity, submittedQuery]);

  const loadAll = async () => {
    const items: LibraryPageData["items"] = [];
    let total = 0;
    do {
      const params = new URLSearchParams({ limit: "100", offset: String(items.length) });
      if (entity === "meal" || entity === "dailyPlan") params.set("include_drafts", "true");
      const next = await apiRequest<LibraryPageData>(`${endpoint}?${params.toString()}`);
      items.push(...next.items);
      total = next.total;
    } while (items.length < total);
    setPage({ items, limit: items.length, offset: 0, search: null, total });
  };

  const beginReorder = async () => {
    setActionsVisible(false); setMode("reorder"); setLoading(true); setError(null); setQuery(""); setSubmittedQuery("");
    try { await loadAll(); } catch (nextError) { setMode("list"); setError(userFacingError(nextError)); } finally { setLoading(false); }
  };

  const saveOrder = async () => {
    if (!page) return;
    setSubmitting(true);
    try {
      const result = await apiRequest<{ message: string }>(`${endpoint}/order`, { body: JSON.stringify({ ordered_ids: page.items.map((item) => item.id) }), headers: { "Content-Type": "application/json" }, method: "PUT" });
      setMode("list"); Alert.alert("Listo", result.message); await load({ refresh: true });
    } catch (nextError) { setError(userFacingError(nextError)); } finally { setSubmitting(false); }
  };

  const confirmDelete = () => {
    if (!selectedIds.size) return;
    Alert.alert("Eliminar elementos", `¿Eliminar ${selectedIds.size} elemento(s)? Esta acción no se puede deshacer.`, [{ text: "Cancelar", style: "cancel" }, { text: "Eliminar", style: "destructive", onPress: () => void deleteSelected() }]);
  };

  const deleteSelected = async () => {
    setSubmitting(true);
    try {
      const result = await apiRequest<{ message: string }>(`${endpoint}/bulk-delete`, { body: JSON.stringify({ item_ids: [...selectedIds] }), headers: { "Content-Type": "application/json" }, method: "POST" });
      setSelectedIds(new Set()); setMode("list"); Alert.alert("Listo", result.message); await load({ refresh: true });
    } catch (nextError) { setError(userFacingError(nextError)); } finally { setSubmitting(false); }
  };

  const moveItem = (index: number, direction: -1 | 1) => setPage((current) => {
    if (!current) return current;
    const target = index + direction;
    if (target < 0 || target >= current.items.length) return current;
    const items = [...current.items]; [items[index], items[target]] = [items[target], items[index]];
    return { ...current, items };
  });

  useFocusEffect(useCallback(() => {
    if (mode === "list") void load();
  }, [load, mode]));

  if (status === "anonymous") return <Redirect href="/login" />;

  return (
    <ScrollView
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
      onScroll={({ nativeEvent }) => {
        const visible = nativeEvent.contentOffset.y > 1;
        if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible);
        const pinned = nativeEvent.contentOffset.y >= searchOffset.current;
        if (pinned !== searchPinned) setSearchPinned(pinned);
      }}
      refreshControl={<RefreshControl onRefresh={() => void load({ refresh: true })} refreshing={refreshing} tintColor={tokens.color.interactivePrimary} />}
      scrollEventThrottle={16}
      stickyHeaderIndices={[1]}
      style={styles.screen}>
      <CollectionPageHeader count={page?.total} countIcon={entity === "program" ? "week" : entity} entity={entity} title={title} />
      <View onLayout={({ nativeEvent }) => { searchOffset.current = nativeEvent.layout.y; }} style={[styles.stickySearch, searchPinned && styles.stickySearchPinned]}>
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
      </View>
      {mode === "list" ? <Button label={createLabels[entity]} onPress={() => router.push({ pathname: "/libraries/create", params: { entity } })} /> : null}
      {mode !== "list" ? <View style={styles.modeBar}><View style={styles.modeCopy}><Text style={styles.modeTitle}>{mode === "reorder" ? "Reordenar" : "Seleccionar para eliminar"}</Text>{mode === "delete" ? <Text style={styles.modeCount}>{selectedIds.size} seleccionado(s)</Text> : null}</View><Button label="Cancelar" onPress={() => { setMode("list"); setSelectedIds(new Set()); void load(); }} variant="secondary" />{mode === "reorder" ? <Button label="Guardar" loading={submitting} onPress={() => void saveOrder()} /> : <Button disabled={!selectedIds.size} label="Eliminar" loading={submitting} onPress={confirmDelete} variant="danger" />}</View> : null}
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
      {page?.items.map((item, index) => <View key={`${item.entity}-${item.id}`} style={styles.managedItem}>{mode === "reorder" ? <View style={styles.itemControls}><Text style={styles.position}>{index + 1}</Text><Pressable accessibilityLabel={`Subir ${item.name}`} disabled={index === 0} onPress={() => moveItem(index, -1)} style={[styles.controlButton, index === 0 && styles.disabled]}><ChevronUp color={tokens.color.textMain} size={22} /></Pressable><Pressable accessibilityLabel={`Bajar ${item.name}`} disabled={index === page.items.length - 1} onPress={() => moveItem(index, 1)} style={[styles.controlButton, index === page.items.length - 1 && styles.disabled]}><ChevronDown color={tokens.color.textMain} size={22} /></Pressable></View> : mode === "delete" ? <Pressable accessibilityLabel={`${selectedIds.has(item.id) ? "Deseleccionar" : "Seleccionar"} ${item.name}`} onPress={() => setSelectedIds((current) => { const next = new Set(current); if (next.has(item.id)) next.delete(item.id); else next.add(item.id); return next; })} style={styles.selectionRow}>{selectedIds.has(item.id) ? <Check color={tokens.color.interactivePrimary} size={22} /> : <Square color={tokens.color.textMuted} size={22} />}<Text style={styles.selectionLabel}>{selectedIds.has(item.id) ? "Seleccionado" : "Seleccionar"}</Text></Pressable> : null}<LibraryCard apiRequest={apiRequest} interactive={mode === "list"} item={item} onChanged={() => void load({ refresh: true })} /></View>)}
      {mode === "list" && page && page.items.length < page.total ? (
        <Button
          label={`Cargar más (${page.total - page.items.length})`}
          loading={loadingMore}
          onPress={() => void load({ append: true, offset: page.items.length })}
          variant="secondary"
        />
      ) : null}
      <LibraryListActions canCompare={entity !== "program"} onClose={() => setActionsVisible(false)} onCompare={() => { setActionsVisible(false); const kind = entity === "food" ? "foods" : entity === "meal" ? "meals" : "dailyplans"; router.push(`/comparator?kind=${kind}`); }} onDelete={() => { setActionsVisible(false); setSelectedIds(new Set()); setMode("delete"); }} onReorder={() => void beginReorder()} visible={actionsVisible} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  content: { flexGrow: 1, gap: tokens.spacing.lg, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  stickySearch: { backgroundColor: tokens.color.surfaceApp, borderBottomColor: "transparent", borderBottomWidth: 1, marginHorizontal: -tokens.spacing.screen, paddingBottom: tokens.spacing.sm, paddingHorizontal: tokens.layout.reducedInset, paddingTop: 0, zIndex: 3 },
  stickySearchPinned: { borderBottomColor: tokens.color.borderDefault },
  searchField: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.lg, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, minHeight: 44, paddingHorizontal: tokens.spacing.md },
  searchInput: { color: tokens.color.textMain, flex: 1, fontSize: 16, minHeight: 42, paddingVertical: 0 },
  clearButton: { alignItems: "center", height: 40, justifyContent: "center", width: 36 },
  modeBar: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.lg, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, padding: tokens.spacing.sm },
  modeCopy: { flex: 1, minWidth: 0 }, modeTitle: { color: tokens.color.textMain, fontSize: 15, fontWeight: "800" }, modeCount: { color: tokens.color.textMuted, fontSize: 12, marginTop: 2 },
  managedItem: { gap: tokens.spacing.sm }, itemControls: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "flex-end" }, position: { color: tokens.color.textMuted, fontSize: 13, fontWeight: "700", marginRight: "auto" }, controlButton: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, height: 42, justifyContent: "center", width: 48 }, disabled: { opacity: 0.35 }, selectionRow: { alignItems: "center", alignSelf: "flex-start", flexDirection: "row", gap: tokens.spacing.sm, minHeight: 42 }, selectionLabel: { color: tokens.color.textMain, fontSize: 14, fontWeight: "700" },
  loading: { alignItems: "center", flex: 1, gap: tokens.spacing.md, justifyContent: "center", minHeight: 240 },
  emptyState: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderStyle: "dashed", borderWidth: 1, gap: tokens.spacing.sm, padding: tokens.spacing.xxl },
  emptySymbol: { fontSize: tokens.type.hero, fontWeight: "300" },
  emptyTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800", textAlign: "center" },
  emptyDescription: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23, textAlign: "center" },
});
