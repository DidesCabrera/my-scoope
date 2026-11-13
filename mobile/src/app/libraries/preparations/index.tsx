import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Alert, ScrollView, StyleSheet, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { PersonalPreparation } from "@/api/preparations";
import type { EntitlementsData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { PreparationCardActions } from "@/components/preparations/preparation-card-actions";
import { PreparationLibraryCard } from "@/components/preparations/preparation-library-card";
import { pickerHref } from "@/components/pickers/picker-routes";
import { Button, Card, CollectionEmptyState, CollectionPageHeader, InlineNotice, LoadingState, SearchField } from "@/components/ui";
import { tokens } from "@/design/tokens";

export default function PreparationsLibraryScreen() {
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [items, setItems] = useState<PersonalPreparation[]>([]);
  const [available, setAvailable] = useState(false);
  const [allowed, setAllowed] = useState(false);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<PersonalPreparation | null>(null);
  const [actionsVisible, setActionsVisible] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const entitlements = await apiRequest<EntitlementsData>("/api/v1/entitlements", { cache: "no-store" });
      const enabled = Boolean(entitlements.workspace_features?.personal_preparations_available);
      const canUse = Boolean(entitlements.workspace_features?.can_use_personal_preparations);
      setAvailable(enabled);
      setAllowed(canUse);
      if (canUse) {
        const all: PersonalPreparation[] = [];
        let total = 0;
        do {
          const page = await apiRequest<{ items: PersonalPreparation[]; total: number }>(`/api/v1/library/preparations?limit=100&offset=${all.length}`);
          all.push(...page.items);
          total = page.total;
          if (!page.items.length) break;
        } while (all.length < total);
        setItems(all);
      } else setItems([]);
    } catch (failure) { setError(userFacingError(failure)); }
    finally { setLoading(false); }
  }, [apiRequest]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      createAction: available && allowed ? { label: "Crear preparación", onPress: () => router.push("/libraries/preparations/new" as Href) } : undefined,
      secondaryAction: { icon: "search", label: "Explorar preparaciones globales", onPress: () => router.push("/explore/preparations" as Href) },
      mode: "default", title: "Mis Preparaciones",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [allowed, available, router, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !items.length) return <LoadingState label="Cargando preparaciones…" />;
  const normalized = query.trim().toLocaleLowerCase("es");
  const visible = items.filter((item) => item.name.toLocaleLowerCase("es").includes(normalized));
  const rename = async (name: string) => {
    if (!selected) return;
    if (selected.is_draft) {
      await apiRequest<PersonalPreparation>(`/api/v1/library/preparations/${selected.id}/draft`, { method: "PATCH", body: JSON.stringify({ name }) });
    } else {
      await apiRequest<PersonalPreparation>(`/api/v1/library/preparations/${selected.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name,
          ...(selected.yield_is_manual ? { yield_g: selected.yield_g } : {}),
          default_portion_g: selected.default_portion_g,
          ingredients: selected.recipe_ingredients.map(({ food_id, quantity_g }) => ({ food_id, quantity_g })),
        }),
      });
    }
    setItems((current) => current.map((item) => item.id === selected.id ? { ...item, name } : item));
    setSelected((current) => current ? { ...current, name } : null);
  };
  const remove = () => {
    if (!selected) return;
    const { id, name } = selected;
    Alert.alert("Eliminar preparación", `¿Eliminar ${name} de tu biblioteca? Las comidas existentes conservarán su composición.`, [
      { text: "Cancelar", style: "cancel" },
      { text: "Eliminar", style: "destructive", onPress: () => {
        void apiRequest(`/api/v1/library/preparations/${id}`, { method: "DELETE" })
          .then(() => { setItems((current) => current.filter((item) => item.id !== id)); setSelected(null); })
          .catch((failure) => Alert.alert("No pudimos eliminarla", userFacingError(failure)));
      } },
    ]);
  };
  return <>
  <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false} style={styles.screen}>
    <CollectionPageHeader count={available && allowed ? items.length : undefined} entity="preparation" title="Mis Preparaciones" />
    {available && allowed ? <View style={styles.search}><SearchField accessibilityLabel="Buscar preparaciones" onChangeText={setQuery} onClear={() => setQuery("")} placeholder="Buscar por nombre" value={query} /></View> : null}
    {error ? <Card><InlineNotice tone="error">{error}</InlineNotice><Button label="Reintentar" onPress={() => void load()} variant="secondary" /></Card> : null}
    {!available ? <Card><InlineNotice tone="info">La biblioteca de preparaciones aún no está disponible.</InlineNotice></Card> : null}
    {available && !allowed ? <Card><InlineNotice tone="info">Las preparaciones personales están disponibles con el plan Pro.</InlineNotice><Button label="Conocer Pro" onPress={() => router.push("/subscription" as Href)} /></Card> : null}
    {available && allowed && !visible.length ? <CollectionEmptyState description={normalized ? "Prueba con otra búsqueda." : "Registra una preparación para reutilizarla en tus comidas."} title={normalized ? "Sin resultados" : "Aún no tienes preparaciones"} /> : null}
    {available && allowed ? visible.map((item) => <PreparationLibraryCard item={item} key={item.id} onMore={item.is_personal && item.is_active ? () => { setSelected(item); setActionsVisible(true); } : undefined} onOpen={() => router.push(item.is_draft ? pickerHref("food-to-preparation", { preparationId: item.id, returnTo: `/libraries/preparations/${item.id}` }) : `/libraries/preparations/${item.id}` as Href)} />) : null}
  </ScrollView>
  {selected ? <PreparationCardActions name={selected.name} onClose={() => setActionsVisible(false)} onDelete={remove} onRename={rename} visible={actionsVisible} /> : null}
  </>;
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, gap: tokens.spacing.lg, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  search: { marginHorizontal: -tokens.spacing.screen, paddingHorizontal: tokens.layout.reducedInset },
});
