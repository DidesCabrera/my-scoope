import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, View, type NativeScrollEvent, type NativeSyntheticEvent } from "react-native";

import { userFacingError } from "@/api/errors";
import type { Supplement } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { EntityDetailPage, EntityDetailSection } from "@/components/details";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { isHeaderIdentityVisible } from "@/components/navigation/header-scroll";
import { SupplementActionsSheet } from "@/components/supplements/supplement-actions-sheet";
import { SupplementInformationTable } from "@/components/supplements/supplement-information-table";
import { Button, InlineNotice, LoadingState } from "@/components/ui";
import { tokens } from "@/design/tokens";

const formLabels: Record<string, string> = {
  capsule: "Cápsula",
  drop: "Gota",
  g: "g",
  gummy: "Gomita",
  iu: "UI",
  liquid: "Líquido",
  mcg: "mcg",
  mg: "mg",
  ml: "ml",
  powder: "Polvo",
  sachet: "Sobre",
  scoop: "Medida",
  softgel: "Cápsula blanda",
  tablet: "Comprimido",
  tsp: "Cucharadita",
};

const unitLabels: Record<string, { plural?: string; singular: string }> = {
  capsule: { plural: "cápsulas", singular: "cápsula" },
  drop: { plural: "gotas", singular: "gota" },
  g: { singular: "g" },
  gummy: { plural: "gomitas", singular: "gomita" },
  iu: { singular: "UI" },
  mcg: { singular: "mcg" },
  mg: { singular: "mg" },
  ml: { singular: "ml" },
  sachet: { plural: "sobres", singular: "sobre" },
  scoop: { plural: "medidas", singular: "medida" },
  softgel: { plural: "cápsulas blandas", singular: "cápsula blanda" },
  tablet: { plural: "comprimidos", singular: "comprimido" },
  tsp: { plural: "cucharaditas", singular: "cucharadita" },
};

function amountLabel(quantity: string, unit: string) {
  const parsed = Number(quantity);
  const formatted = Number.isFinite(parsed) ? parsed.toLocaleString("es-CL", { maximumFractionDigits: 3 }) : quantity;
  const labels = unitLabels[unit];
  const displayUnit = labels ? parsed === 1 ? labels.singular : labels.plural ?? labels.singular : unit;
  return `${formatted} ${displayUnit}`.trim();
}

const nutritionRows = [
  { id: "energy_kcal", label: "Calorías", unit: "kcal" },
  { id: "protein_g", label: "Proteínas", unit: "g" },
  { id: "fat_g", label: "Grasas totales", unit: "g" },
  { id: "saturated_fat_g", label: "Grasas saturadas", unit: "g" },
  { id: "carbs_g", label: "Carbohidratos", unit: "g" },
  { id: "sugar_g", label: "Azúcares", unit: "g" },
  { id: "fiber_g", label: "Fibra", unit: "g" },
  { id: "sodium_mg", label: "Sodio", unit: "mg" },
] as const;

function nutritionValue(value: string | null | undefined, unit: string) {
  if (value == null || value === "") return "-";
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return `${number.toLocaleString("es-CL", { maximumFractionDigits: 1 })} ${unit}`;
}

export default function SupplementDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [item, setItem] = useState<Supplement | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionsVisible, setActionsVisible] = useState(false);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const openActions = useCallback(() => setActionsVisible(true), []);
  const remove = useCallback(() => {
    if (!item) return;
    setActionsVisible(false);
    Alert.alert("Eliminar suplemento", "Se quitará de tu biblioteca. Las ingestas guardadas conservarán su descripción.", [
      { text: "Cancelar", style: "cancel" },
      { text: "Eliminar", style: "destructive", onPress: () => { void apiRequest(`/api/v1/library/supplements/${item.id}`, { method: "DELETE" }).then(() => router.replace("/libraries/supplements" as Href)).catch((nextError) => setError(userFacingError(nextError))); } },
    ]);
  }, [apiRequest, item, router]);
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItem(await apiRequest<Supplement>(`/api/v1/library/supplements/${id}`));
    } catch (nextError) {
      setError(userFacingError(nextError));
      setItem(null);
    } finally {
      setLoading(false);
    }
  }, [apiRequest, id]);

  useFocusEffect(useCallback(() => {
    if (status === "authenticated") void load();
  }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      action: item ? { icon: "more", label: `Más acciones para ${item.name}`, onPress: openActions } : undefined,
      fallback: "/libraries/supplements" as Href,
      identityVisible: compactHeaderVisible,
      mode: "back",
      title: item?.name ?? "Detalle de suplemento",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, item, openActions, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !item) return <LoadingState label="Cargando suplemento…" />;
  if (!item) return <View style={styles.loading}>{error ? <InlineNotice tone="error">{error}</InlineNotice> : null}<Button label="Reintentar" onPress={() => void load()} variant="secondary" /></View>;

  const handleScroll = ({ nativeEvent }: NativeSyntheticEvent<NativeScrollEvent>) => setCompactHeaderVisible(isHeaderIdentityVisible(nativeEvent.contentOffset.y));
  const hasInformation = Boolean(item.brand || item.form || item.description);
  const hasDose = Boolean(item.default_quantity && item.default_unit);
  return <>
    <ScrollView contentContainerStyle={styles.content} onScroll={handleScroll} scrollEventThrottle={16} showsVerticalScrollIndicator={false} style={styles.screen}>
      <EntityDetailPage
        entity="supplement"
        eyebrow="Suplemento"
        indicators={item.components.length ? [{ icon: "supplement", label: item.components.length === 1 ? "componente" : "componentes", value: item.components.length }] : undefined}
        showNutrition={false}
        subtitle={item.brand || undefined}
        title={item.name}>
        {hasInformation || hasDose ? <EntityDetailSection title="Información del suplemento">
          {item.brand || item.form || hasDose ? <SupplementInformationTable items={[
            ...(item.brand ? [{ id: "brand", label: "Marca", value: item.brand }] : []),
            ...(item.form ? [{ id: "form", label: "Forma", value: formLabels[item.form] ?? item.form }] : []),
            ...(hasDose ? [{ id: "default-dose", label: "Dosis predeterminada", value: amountLabel(item.default_quantity ?? "", item.default_unit) }] : []),
          ]} /> : null}
          {item.description ? <Text style={styles.description}>{item.description}</Text> : null}
        </EntityDetailSection> : null}
        {item.components.length ? <EntityDetailSection detail={`${item.components.length} ${item.components.length === 1 ? "componente" : "componentes"}`} title="Componentes">
          <SupplementInformationTable
            items={item.components.map((component, index) => ({ id: `${component.name}-${index}`, label: component.name, value: amountLabel(component.quantity, component.unit) }))}
            labelHeader="Componente"
            valueHeader="Cantidad"
          />
        </EntityDetailSection> : null}
        <EntityDetailSection detail="Por dosis predeterminada" title="Información nutricional">
          <SupplementInformationTable
            items={nutritionRows.map((row) => ({
              id: row.id,
              label: row.label,
              value: nutritionValue(item.nutrition?.[row.id], row.unit),
            }))}
            labelHeader="Nutriente"
            valueHeader="Por dosis"
          />
        </EntityDetailSection>
        {item.user_information ? <EntityDetailSection title="Notas personales"><Text style={styles.description}>{item.user_information}</Text></EntityDetailSection> : null}
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      </EntityDetailPage>
    </ScrollView>
    <SupplementActionsSheet name={item.name} onClose={() => setActionsVisible(false)} onDelete={remove} onEdit={() => {
      setActionsVisible(false);
      router.push(`/libraries/supplements/${item.id}/edit` as Href);
    }} visible={actionsVisible} />
  </>;
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  description: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 24 },
  loading: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, flex: 1, gap: tokens.spacing.md, justifyContent: "center", padding: tokens.spacing.screen },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
});
