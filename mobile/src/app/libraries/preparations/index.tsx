import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { ScrollView, StyleSheet, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { PersonalPreparation } from "@/api/preparations";
import type { EntitlementsData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
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
  return <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false} style={styles.screen}>
    <CollectionPageHeader count={available && allowed ? items.length : undefined} entity="preparation" title="Mis Preparaciones" />
    {available && allowed ? <View style={styles.search}><SearchField accessibilityLabel="Buscar preparaciones" onChangeText={setQuery} onClear={() => setQuery("")} placeholder="Buscar por nombre" value={query} /></View> : null}
    {error ? <Card><InlineNotice tone="error">{error}</InlineNotice><Button label="Reintentar" onPress={() => void load()} variant="secondary" /></Card> : null}
    {!available ? <Card><InlineNotice tone="info">La biblioteca de preparaciones aún no está disponible.</InlineNotice></Card> : null}
    {available && !allowed ? <Card><InlineNotice tone="info">Las preparaciones personales están disponibles con el plan Pro.</InlineNotice><Button label="Conocer Pro" onPress={() => router.push("/subscription" as Href)} /></Card> : null}
    {available && allowed && !visible.length ? <CollectionEmptyState description={normalized ? "Prueba con otra búsqueda." : "Registra una preparación para reutilizarla en tus comidas."} title={normalized ? "Sin resultados" : "Aún no tienes preparaciones"} /> : null}
    {available && allowed ? visible.map((item) => <PreparationLibraryCard item={item} key={item.id} onOpen={() => router.push(item.is_draft ? pickerHref("food-to-preparation", { preparationId: item.id, returnTo: `/libraries/preparations/${item.id}` }) : `/libraries/preparations/${item.id}` as Href)} />) : null}
  </ScrollView>;
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, gap: tokens.spacing.lg, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  search: { marginHorizontal: -tokens.spacing.screen, paddingHorizontal: tokens.layout.reducedInset },
});
