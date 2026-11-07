import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { SupplementIntakePreset } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { PickerCardAction } from "@/components/pickers/picker-card-action";
import { PickerEntryTabs } from "@/components/pickers/picker-entry-tabs";
import { SupplementIntakePresetCard } from "@/components/supplements/supplement-intake-preset-card";
import { InlineNotice, LoadingState, SearchField, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { internalHref } from "@/navigation/internal-href";

export default function AddSupplementIntakeScreen() {
  const { calendarizedDayId, id, pinned, returnTo } = useLocalSearchParams<{ calendarizedDayId?: string; id: string; pinned?: string; returnTo?: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [items, setItems] = useState<SupplementIntakePreset[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const returnHref = internalHref(returnTo) ?? `/libraries/daily-plans/${id}` as Href;
  const contextParams = {
    ...(calendarizedDayId ? { calendarizedDayId } : {}),
    ...(pinned === "1" ? { pinned: "1" } : {}),
  };
  const addHref = `/libraries/daily-plans/${id}/supplement-intakes/add?returnTo=${encodeURIComponent(String(returnHref))}${calendarizedDayId ? `&calendarizedDayId=${encodeURIComponent(calendarizedDayId)}` : ""}${pinned === "1" ? "&pinned=1" : ""}` as Href;

  const close = useCallback(() => { if (router.canGoBack()) router.back(); else router.replace(returnHref); }, [returnHref, router]);
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ action: { label: "Cancelar", onPress: close }, fallback: returnHref, forceFallback: true, mode: "back", title: "Agregar ingesta" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [close, returnHref, setHeaderPresentation]));
  useFocusEffect(useCallback(() => {
    let active = true;
    setLoading(true); setError(null);
    void apiRequest<{ items: SupplementIntakePreset[] }>("/api/v1/library/supplement-intake-presets")
      .then((page) => { if (active) setItems(page.items); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest]));

  const normalizedQuery = query.trim().toLocaleLowerCase("es");
  const visible = useMemo(() => items.filter((item) => `${item.name} ${item.items.map((row) => row.supplement.name ?? "").join(" ")}`.toLocaleLowerCase("es").includes(normalizedQuery)), [items, normalizedQuery]);
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !items.length) return <LoadingState label="Cargando tus ingestas…" />;

  return <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
    <ScrollView automaticallyAdjustKeyboardInsets contentContainerStyle={styles.content} keyboardDismissMode="on-drag" keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false} stickyHeaderIndices={[0]}>
      <View style={styles.sticky}>
        <PickerEntryTabs createLabel="Crear ingesta" onCreate={() => router.push({ pathname: "/libraries/supplements/intakes/new", params: { returnTo: String(addHref) } })} />
        <SearchField accessibilityLabel="Buscar ingesta" autoCapitalize="words" bleed onChangeText={setQuery} placeholder="Escribe el nombre de una ingesta" value={query} />
      </View>
      <View style={styles.options}>
        {visible.map((item) => <SupplementIntakePresetCard contained item={item} key={item.id}>
          <View style={styles.cardAction}><PickerCardAction label="Seleccionar" onPress={() => router.push({ pathname: "/libraries/daily-plans/[id]/supplement-intakes/configure", params: { id, presetId: String(item.id), returnTo: String(returnHref), ...contextParams } })} subject={item.name} variant="mutedFullWidth" /></View>
        </SupplementIntakePresetCard>)}
        {!loading && !visible.length ? <Text style={textStyles.muted}>{normalizedQuery ? "No encontramos resultados." : "Aún no tienes ingestas guardadas. Puedes crear una nueva para esta minuta."}</Text> : null}
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
