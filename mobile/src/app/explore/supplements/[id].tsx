import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Linking, ScrollView, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { Button, CollectionPageHeader, InlineNotice, LoadingState } from "@/components/ui";
import { tokens } from "@/design/tokens";
import type { CatalogSupplement } from "../supplements";

export default function ExploreSupplementDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [item, setItem] = useState<CatalogSupplement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try { setItem(await apiRequest<CatalogSupplement>(`/api/v1/explore/supplements/${id}`)); setError(null); }
    catch (nextError) { setError(userFacingError(nextError)); }
  }, [apiRequest, id]);
  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/explore/supplements" as Href, mode: "back", title: item?.name ?? "Suplemento global" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [item?.name, setHeaderPresentation]));

  const save = async () => {
    if (!item || saving) return;
    setSaving(true);
    try {
      const result = await apiRequest<{ saved_supplement_id: number }>(`/api/v1/explore/supplements/${item.id}/save`, { method: "POST" });
      setItem({ ...item, saved_supplement_id: result.saved_supplement_id });
      setError(null);
    } catch (nextError) { setError(userFacingError(nextError)); }
    finally { setSaving(false); }
  };

  if (status === "anonymous") return <Redirect href="/login" />;
  if (!item && !error) return <LoadingState label="Cargando suplemento…" />;
  return <ScrollView contentContainerStyle={styles.content} style={styles.screen}>
    {item ? <>
      <CollectionPageHeader entity="supplement" title={item.name} />
      {item.brand ? <Text style={styles.text}>Marca: {item.brand}</Text> : <Text style={styles.text}>Referencia general, sin marca ni dosis definida.</Text>}
      <Text style={styles.text}>{item.description}</Text>
      {item.components.map((component) => <Text key={component.name} style={styles.text}>{component.name}: {component.quantity} {component.unit}</Text>)}
      <Text style={styles.source}>Fuente: {item.source_name}. Revisado el {item.reviewed_at}.</Text>
      <Button label="Ver fuente" onPress={() => void Linking.openURL(item.source_url)} variant="secondary" />
      {item.saved_supplement_id ? <Button label="Ver en mi biblioteca" onPress={() => router.push(`/libraries/supplements/${item.saved_supplement_id}` as Href)} variant="primary" /> : <Button label="Guardar en mi biblioteca" loading={saving} onPress={() => void save()} variant="primary" />}
    </> : null}
    {error ? <View><InlineNotice tone="error">{error}</InlineNotice><Button label="Reintentar" onPress={() => void load()} variant="secondary" /></View> : null}
  </ScrollView>;
}

const styles = StyleSheet.create({
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  content: { gap: tokens.spacing.lg, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  text: { color: tokens.color.textMain, fontSize: 16 },
  source: { color: tokens.color.textMuted, fontSize: 14 },
});
