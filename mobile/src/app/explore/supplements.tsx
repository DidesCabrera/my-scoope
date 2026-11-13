import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { ScrollView, StyleSheet, View } from "react-native";

import { userFacingError } from "@/api/errors";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { Button, CollectionEmptyState, CollectionPageHeader, InlineNotice, LoadingState, SearchField, SupplementCard } from "@/components/ui";
import { tokens } from "@/design/tokens";

export type CatalogSupplement = {
  id: number; name: string; brand: string; form: string; description: string;
  components: { name: string; quantity: string; unit: string }[];
  nutrition: Record<string, string | null>; default_quantity: string | null; default_unit: string;
  source_name: string; source_url: string; reviewed_at: string; saved_supplement_id: number | null;
};

export default function ExploreSupplementsScreen() {
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [items, setItems] = useState<CatalogSupplement[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await apiRequest<{ items: CatalogSupplement[] }>("/api/v1/explore/supplements");
      setItems(page.items);
    } catch (nextError) { setError(userFacingError(nextError)); }
    finally { setLoading(false); }
  }, [apiRequest]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/libraries/supplements" as Href, mode: "back", title: "Explorar suplementos" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !items.length) return <LoadingState label="Cargando suplementos…" />;
  const visible = items.filter((item) => `${item.name} ${item.brand}`.toLocaleLowerCase("es").includes(query.trim().toLocaleLowerCase("es")));
  return <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false} style={styles.screen}>
    <CollectionPageHeader count={items.length} countLabels={{ plural: "Suplementos", singular: "Suplemento" }} entity="supplement" title="Explorar suplementos" />
    <SearchField accessibilityLabel="Buscar suplementos globales" onChangeText={setQuery} onClear={() => setQuery("")} placeholder="Buscar por nombre o marca" value={query} />
    {error ? <View><InlineNotice tone="error">{error}</InlineNotice><Button label="Reintentar" onPress={() => void load()} variant="secondary" /></View> : null}
    {!loading && !visible.length && !error ? <CollectionEmptyState title="Sin resultados" description="Prueba con otra búsqueda." /> : null}
    {visible.map((item) => <SupplementCard brand={item.brand} componentCount={item.components.length} key={item.id} name={item.name} onOpen={() => router.push(`/explore/supplements/${item.id}` as Href)} quantity={item.default_quantity} unit={item.default_unit} />)}
  </ScrollView>;
}

const styles = StyleSheet.create({
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  content: { gap: tokens.spacing.lg, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
});
