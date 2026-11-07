import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { Supplement } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { PickerCardAction } from "@/components/pickers/picker-card-action";
import { PickerEntryTabs } from "@/components/pickers/picker-entry-tabs";
import { stagePresetSupplementSelection } from "@/components/supplements/supplement-intake-preset-selection-handoff";
import { InlineNotice, LoadingState, SearchField, SupplementCard, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { internalHref } from "@/navigation/internal-href";

export default function PresetSupplementSelectionScreen() {
  const { presetId = "new", returnTo, selectedIds = "", selectionSession = "1" } = useLocalSearchParams<{ presetId?: string; returnTo?: string; selectedIds?: string; selectionSession?: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [items, setItems] = useState<Supplement[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestedReturnHref = internalHref(returnTo);
  const formHref = `/libraries/supplements/intakes/${presetId === "new" ? "new" : `${presetId}/edit`}${requestedReturnHref ? `?returnTo=${encodeURIComponent(String(requestedReturnHref))}` : ""}` as Href;
  const selectorHref = `/libraries/supplements/intakes/select?presetId=${encodeURIComponent(presetId)}&selectedIds=${encodeURIComponent(selectedIds)}&selectionSession=${encodeURIComponent(selectionSession)}${requestedReturnHref ? `&returnTo=${encodeURIComponent(String(requestedReturnHref))}` : ""}` as Href;
  const excludedIds = useMemo(() => new Set(selectedIds.split(",").map(Number).filter((value) => Number.isInteger(value) && value > 0)), [selectedIds]);
  const close = useCallback(() => { if (router.canGoBack()) router.back(); else router.replace(formHref); }, [formHref, router]);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ action: { label: "Cancelar", onPress: close }, fallback: formHref, mode: "back", title: "Agregar suplemento" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [close, formHref, setHeaderPresentation]));
  useFocusEffect(useCallback(() => {
    let active = true;
    setLoading(true); setError(null);
    void apiRequest<{ items: Supplement[] }>("/api/v1/library/supplements")
      .then((page) => { if (active) setItems(page.items); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !items.length) return <LoadingState label="Cargando tus suplementos…" />;
  const normalizedQuery = query.trim().toLocaleLowerCase("es");
  const visible = items.filter((item) => !excludedIds.has(item.id) && `${item.name} ${item.brand}`.toLocaleLowerCase("es").includes(normalizedQuery));
  const select = (item: Supplement) => {
    stagePresetSupplementSelection({ presetId, selectionSession, supplementId: item.id });
    close();
  };

  return <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
    <ScrollView automaticallyAdjustKeyboardInsets contentContainerStyle={styles.content} keyboardDismissMode="on-drag" keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false} stickyHeaderIndices={[0]}>
      <View style={styles.sticky}>
        <PickerEntryTabs createLabel="Crear suplemento" onCreate={() => router.push({ pathname: "/libraries/supplements/new", params: { returnTo: String(selectorHref) } })} />
        <SearchField accessibilityLabel="Buscar suplemento" autoCapitalize="words" bleed onChangeText={setQuery} placeholder="Escribe el nombre de un suplemento" value={query} />
      </View>
      <View style={styles.options}>
        {visible.map((item) => <SupplementCard brand={item.brand} componentCount={item.components.length} contained key={item.id} name={item.name} quantity={item.default_quantity} unit={item.default_unit}>
          <View style={styles.cardAction}><PickerCardAction label="Agregar" onPress={() => select(item)} subject={item.name} variant="mutedFullWidth" /></View>
        </SupplementCard>)}
        {!loading && !visible.length ? <Text style={textStyles.muted}>{normalizedQuery ? "No encontramos resultados." : "No quedan suplementos por agregar."}</Text> : null}
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      </View>
    </ScrollView>
  </SafeAreaView>;
}

const styles = StyleSheet.create({
  cardAction: { marginHorizontal: -6 },
  content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen },
  options: { gap: tokens.spacing.lg, paddingTop: tokens.spacing.md },
  safeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  sticky: { backgroundColor: tokens.color.surfaceApp, marginHorizontal: -tokens.spacing.screen, paddingBottom: tokens.spacing.sm, paddingHorizontal: tokens.spacing.screen, zIndex: 2 },
});
