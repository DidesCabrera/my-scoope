import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { Pencil, Pill, PillBottle, Trash2 } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Alert, ScrollView, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { SupplementIntakePreset } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { EntityDetailPage, EntityDetailSection } from "@/components/details";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ProgramSectionHeader } from "@/components/programs/program-section-header";
import { SupplementIntakeItemsTable, type SupplementIntakeTableItem } from "@/components/supplements/supplement-intake-items-table";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, InlineNotice, LoadingState, SupplementCard } from "@/components/ui";
import { tokens } from "@/design/tokens";

export default function SupplementIntakePresetDetailScreen() {
  const { presetId } = useLocalSearchParams<{ presetId: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [item, setItem] = useState<SupplementIntakePreset | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionsVisible, setActionsVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { setItem(await apiRequest<SupplementIntakePreset>(`/api/v1/library/supplement-intake-presets/${presetId}`)); }
    catch (nextError) { setError(userFacingError(nextError)); setItem(null); }
    finally { setLoading(false); }
  }, [apiRequest, presetId]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      action: item ? { icon: "more", label: `Más acciones para ${item.name}`, onPress: () => setActionsVisible(true) } : undefined,
      fallback: "/libraries/supplements?tab=intakes" as Href,
      forceFallback: true,
      mode: "back",
      title: item?.name ?? "Detalle de ingesta",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [item, setHeaderPresentation]));
  function remove() {
    if (!item) return;
    Alert.alert("Eliminar ingesta", "Se quitará de tus ingestas guardadas. Las minutas que ya la usan no cambiarán.", [
      { text: "Cancelar", style: "cancel" },
      { text: "Eliminar", style: "destructive", onPress: () => { void apiRequest(`/api/v1/library/supplement-intake-presets/${item.id}`, { method: "DELETE" }).then(() => router.replace("/libraries/supplements?tab=intakes" as Href)).catch((nextError) => setError(userFacingError(nextError))); } },
    ]);
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !item) return <LoadingState label="Cargando ingesta…" />;
  if (!item) return <View style={styles.loading}>{error ? <InlineNotice tone="error">{error}</InlineNotice> : null}<Button label="Reintentar" onPress={() => void load()} variant="secondary" /></View>;
  const tableItems: SupplementIntakeTableItem[] = item.items.map((row, index) => ({
    brand: typeof row.supplement.brand === "string" ? row.supplement.brand : undefined,
    id: row.id != null ? `item:${row.id}` : `item:${index}`,
    name: String(row.supplement.name ?? "Suplemento guardado"),
    quantity: row.quantity,
    unit: row.unit,
  }));

  return <>
    <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false} style={styles.screen}>
      <EntityDetailPage
        entity="supplement"
        eyebrow="Ingesta de suplementos"
        identityIcon={PillBottle}
        indicators={[{ icon: "supplement", label: "sups", value: item.items.length }]}
        showNutrition={false}
        title={item.name}>
        <EntityDetailSection detail={`${item.items.length} ${item.items.length === 1 ? "suplemento" : "suplementos"}`} title="Composición de la ingesta">
          <SupplementIntakeItemsTable editable={false} items={tableItems} onOpen={(row) => {
            const index = tableItems.findIndex((candidate) => candidate.id === row.id);
            const supplementId = index >= 0 ? item.items[index]?.supplement_id : null;
            if (supplementId) router.push(`/libraries/supplements/${supplementId}` as Href);
          }} />
        </EntityDetailSection>
        <ProgramSectionHeader icon={Pill} subtitle="Revisa la información de cada suplemento incluido en esta ingesta." title="Detalle de cada suplemento" />
        <View style={styles.cardList}>{item.items.map((row, index) => <SupplementCard
          brand={typeof row.supplement.brand === "string" ? row.supplement.brand : undefined}
          componentCount={Array.isArray(row.supplement.components) ? row.supplement.components.length : 0}
          key={row.id ?? index}
          name={String(row.supplement.name ?? "Suplemento guardado")}
          onOpen={row.supplement_id ? () => router.push(`/libraries/supplements/${row.supplement_id}` as Href) : undefined}
          quantity={row.quantity}
          unit={row.unit}
        />)}</View>
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      </EntityDetailPage>
    </ScrollView>
    <ActionSheetModal onRequestClose={() => setActionsVisible(false)} visible={actionsVisible}>
      <SafeAreaView edges={["left", "right"]} style={styles.sheetSafeArea}>
        <ActionSheetHeader icon={PillBottle} iconColor={tokens.color.supplement} onClose={() => setActionsVisible(false)} title={item.name} />
        <View style={styles.sheetContent}>
          <ActionSheetActions>
            <ActionSheetAction icon={Pencil} label="Editar ingesta" onPress={() => { setActionsVisible(false); router.push(`/libraries/supplements/intakes/${item.id}/edit` as Href); }} />
            <ActionSheetAction destructive icon={Trash2} label="Eliminar ingesta" onPress={() => { setActionsVisible(false); remove(); }} />
          </ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  </>;
}

const styles = StyleSheet.create({
  cardList: { gap: tokens.spacing.lg },
  content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  loading: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, flex: 1, gap: tokens.spacing.md, justifyContent: "center", padding: tokens.spacing.screen },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  sheetContent: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  sheetSafeArea: { backgroundColor: tokens.color.surfaceCard },
});
