import { Redirect, useFocusEffect, useRouter } from "expo-router";
import { Search, X } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Alert, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { NestableScrollContainer } from "react-native-draggable-flatlist";

import { userFacingError } from "@/api/errors";
import type { LibraryEntity, LibraryListActionResult, LibraryPageData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { isHeaderIdentityVisible } from "@/components/navigation/header-scroll";
import { CollectionPageHeader, LoadingState, MacroLoadingIndicator, MutationStatusModal, useMutationStatus } from "@/components/ui";
import { Button, Card, InlineNotice } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

import { LibraryCard } from "./library-card";
import { LibraryListActions } from "./library-list-actions";
import { LibraryListEditor } from "./library-list-editor";

type LibraryListScreenProps = {
  emptyDescription: string;
  endpoint: string;
  entity: LibraryEntity;
  title: string;
};

const createLabels: Record<LibraryEntity, string> = {
  food: "Crear alimento",
  meal: "Crear comida",
  dailyPlan: "Crear plan diario",
  program: "Crear programa",
};

const deleteLabels: Record<LibraryEntity, string> = {
  food: "Eliminar alimentos",
  meal: "Eliminar comidas",
  dailyPlan: "Eliminar planes diarios",
  program: "Eliminar programas",
};

export function LibraryListScreen({ emptyDescription, endpoint, entity, title }: LibraryListScreenProps) {
  const { status, apiRequest } = useSession();
  const router = useRouter();
  const [page, setPage] = useState<LibraryPageData | null>(null);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setHeaderPresentation = useHeaderPresentation();
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [actionsVisible, setActionsVisible] = useState(false);
  const [mode, setMode] = useState<"list" | "edit">("list");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const { clearStatus, runWithStatus, status: mutationStatus } = useMutationStatus();
  const cancelSelection = useCallback(() => setSelectedIds(new Set()), []);
  const finishEdit = useCallback(() => { setSelectedIds(new Set()); setMode("list"); }, []);

  const load = useCallback(async ({ append = false, offset = 0 } = {}) => {
    if (append) setLoadingMore(true);
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

  const beginEdit = async () => {
    setActionsVisible(false); setMode("edit"); setSelectedIds(new Set()); setLoading(true); setError(null); setQuery(""); setSubmittedQuery("");
    try { await loadAll(); } catch (nextError) { setMode("list"); setError(userFacingError(nextError)); } finally { setLoading(false); }
  };

  const saveOrder = async (items: LibraryPageData["items"]) => {
    const previousItems = page?.items ?? [];
    setPage((current) => current ? { ...current, items } : current);
    setSubmitting(true);
    setError(null);
    try {
      await runWithStatus(
        () => apiRequest(`${endpoint}/order`, { body: JSON.stringify({ ordered_ids: items.map((item) => item.id) }), headers: { "Content-Type": "application/json" }, method: "PUT" }),
        { loadingLabel: `Actualizando ${title.toLowerCase()}`, successLabel: "Orden actualizado" },
      );
    } catch (nextError) {
      setPage((current) => current ? { ...current, items: previousItems } : current);
      setError(userFacingError(nextError));
    } finally { setSubmitting(false); }
  };

  const deleteItems = useCallback(async (itemIds: number[]) => {
    if (!itemIds.length) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await apiRequest<LibraryListActionResult>(`${endpoint}/bulk-delete`, { body: JSON.stringify({ item_ids: itemIds }), headers: { "Content-Type": "application/json" }, method: "POST" });
      const affectedIds = new Set(result.affected_ids);
      setPage((current) => current ? { ...current, items: current.items.filter(({ id }) => !affectedIds.has(id)), total: Math.max(0, current.total - affectedIds.size) } : current);
      setSelectedIds((current) => new Set([...current].filter((id) => !affectedIds.has(id))));
      Alert.alert(result.affected_ids.length === 1 ? "Elemento eliminado" : "Elementos eliminados", result.message);
    } catch (nextError) { setError(userFacingError(nextError)); } finally { setSubmitting(false); }
  }, [apiRequest, endpoint]);

  const deleteSelected = useCallback(() => deleteItems([...selectedIds]), [deleteItems, selectedIds]);

  const confirmDeleteItem = (item: LibraryPageData["items"][number]) => {
    Alert.alert(
      `¿Eliminar “${item.name}”?`,
      "Esta acción no se puede deshacer.",
      [{ text: "Cancelar", style: "cancel" }, { text: "Eliminar", style: "destructive", onPress: () => void deleteItems([item.id]) }],
    );
  };

  const confirmDeleteSelected = useCallback(() => {
    if (!selectedIds.size) return;
    Alert.alert(
      deleteLabels[entity],
      `¿Eliminar ${selectedIds.size} elemento(s)? Esta acción no se puede deshacer.`,
      [{ text: "Cancelar", style: "cancel" }, { text: "Eliminar", style: "destructive", onPress: () => void deleteSelected() }],
    );
  }, [deleteSelected, entity, selectedIds.size]);

  const toggleSelected = (item: LibraryPageData["items"][number]) => setSelectedIds((current) => {
    const next = new Set(current);
    if (next.has(item.id)) next.delete(item.id);
    else next.add(item.id);
    return next;
  });

  useFocusEffect(useCallback(() => {
    if (mode === "edit" && selectedIds.size) {
      setHeaderPresentation({
        action: { disabled: submitting, label: "Eliminar", onPress: confirmDeleteSelected },
        identityVisible: true,
        leadingAction: { disabled: submitting, label: "Cancelar", onPress: cancelSelection },
        mode: "back",
        title: deleteLabels[entity],
      });
    } else {
      setHeaderPresentation({
        mode: "library-list",
        action: mode === "list"
          ? { icon: "more", label: `Acciones de ${title}`, onPress: () => setActionsVisible(true) }
          : { disabled: loading || submitting, label: "Listo", onPress: finishEdit },
        createAction: mode === "list" ? { label: createLabels[entity], onPress: () => router.push({ pathname: "/libraries/create", params: { entity } }) } : undefined,
        entity,
        identityVisible: compactHeaderVisible,
        title,
      });
    }
    return () => setHeaderPresentation({ mode: "default" });
  }, [cancelSelection, compactHeaderVisible, confirmDeleteSelected, entity, finishEdit, loading, mode, router, selectedIds.size, setHeaderPresentation, submitting, title]));

  useFocusEffect(useCallback(() => {
    if (mode === "list") void load();
  }, [load, mode]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && mode === "list" && !page) return <LoadingState label="Cargando tu librería…" />;

  return (
    <NestableScrollContainer
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
      onScroll={({ nativeEvent }) => setCompactHeaderVisible(isHeaderIdentityVisible(nativeEvent.contentOffset.y))}
      showsVerticalScrollIndicator={false}
      scrollEventThrottle={16}
      stickyHeaderIndices={mode === "list" ? [1] : undefined}
      style={styles.screen}>
      <CollectionPageHeader count={page?.total} countIcon={entity === "program" ? "week" : entity} entity={entity} title={title} />
      {mode === "list" ? <View style={styles.stickySearch}>
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
      </View> : null}
      {error ? (
        <Card>
          <InlineNotice tone="error">{error}</InlineNotice>
          <Button label="Reintentar" onPress={() => void (mode === "edit" ? beginEdit() : load())} variant="secondary" />
        </Card>
      ) : null}
      {loading && (mode === "edit" || !page) ? (
        <View style={styles.loading}>
          <MacroLoadingIndicator accessibilityLabel="Cargando tu librería" />
        </View>
      ) : null}
      {!loading && page?.items.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={[styles.emptySymbol, { color: tokens.color[entity] }]}>＋</Text>
          <Text style={styles.emptyTitle}>{submittedQuery ? "Sin resultados" : `Aún no tienes ${title.toLowerCase()}`}</Text>
          <Text style={styles.emptyDescription}>{submittedQuery ? "Prueba con otra búsqueda." : emptyDescription}</Text>
        </View>
      ) : null}
      {mode === "edit" && !loading && page?.items.length ? <LibraryListEditor busy={submitting} items={page.items} onDelete={confirmDeleteItem} onReorder={saveOrder} onToggle={toggleSelected} selectedIds={selectedIds} /> : null}
      {mode === "list" ? page?.items.map((item) => <View key={`${item.entity}-${item.id}`} style={styles.managedItem}><LibraryCard apiRequest={apiRequest} item={item} onChanged={() => load()} /></View>) : null}
      {mode === "list" && page && page.items.length < page.total ? (
        <Button
          label={`Cargar más (${page.total - page.items.length})`}
          loading={loadingMore}
          onPress={() => void load({ append: true, offset: page.items.length })}
          variant="secondary"
        />
      ) : null}
      <LibraryListActions canCompare={entity !== "program"} onClose={() => setActionsVisible(false)} onCompare={() => { setActionsVisible(false); const kind = entity === "food" ? "foods" : entity === "meal" ? "meals" : "dailyplans"; router.push(`/comparator?create=1&kind=${kind}`); }} onEdit={() => void beginEdit()} visible={actionsVisible} />
      <MutationStatusModal onFinished={clearStatus} status={mutationStatus} />
    </NestableScrollContainer>
  );
}

const styles = StyleSheet.create({
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  content: { flexGrow: 1, gap: tokens.spacing.lg, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  stickySearch: { backgroundColor: tokens.color.surfaceApp, marginHorizontal: -tokens.spacing.screen, paddingBottom: tokens.spacing.sm, paddingHorizontal: tokens.layout.reducedInset, paddingTop: tokens.spacing.xs, zIndex: 3 },
  searchField: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, minHeight: 38, paddingHorizontal: tokens.spacing.md },
  searchInput: { color: tokens.color.textMain, flex: 1, fontSize: 16, minHeight: 36, paddingVertical: 0 },
  clearButton: { alignItems: "center", height: 34, justifyContent: "center", width: 34 },
  managedItem: { gap: tokens.spacing.sm },
  loading: { alignItems: "center", flex: 1, gap: tokens.spacing.md, justifyContent: "center", minHeight: 240 },
  emptyState: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderStyle: "dashed", borderWidth: 1, gap: tokens.spacing.sm, padding: tokens.spacing.xxl },
  emptySymbol: { fontSize: tokens.type.hero, fontWeight: "300" },
  emptyTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800", textAlign: "center" },
  emptyDescription: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23, textAlign: "center" },
});
