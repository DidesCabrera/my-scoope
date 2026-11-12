import { type Href, Redirect, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { PersonalPreparation } from "@/api/preparations";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { formatPreparationAllergens, formatPreparationNumber, preparationStateLabel } from "@/components/preparations/preparation-ingredients-card";
import { ContentPanel, LoadingState, Screen } from "@/components/ui";
import { RecoverableErrorState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";

function InformationRow({ label, value }: { label: string; value: string }) {
  return <View style={styles.row}><Text style={styles.label}>{label}</Text><Text style={styles.value}>{value}</Text></View>;
}

export default function PreparationInformationScreen() {
  const { id, units, grams } = useLocalSearchParams<{ id: string; units?: string; grams?: string }>();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [detail, setDetail] = useState<PersonalPreparation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const validId = Number.isInteger(Number(id)) && Number(id) > 0;

  const load = useCallback(async () => {
    if (!validId) return;
    setLoading(true);
    setError(null);
    const portion = units && Number(units) > 0 ? `?units=${encodeURIComponent(units)}` : grams && Number(grams) > 0 ? `?grams=${encodeURIComponent(grams)}` : "";
    try {
      setDetail(await apiRequest<PersonalPreparation>(`/api/v1/preparations/${id}${portion}`));
    } catch (failure) {
      setError(userFacingError(failure));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, grams, id, units, validId]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: `/libraries/preparations/${id}` as Href, mode: "back", title: "Información del elemento" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [id, setHeaderPresentation]));

  if (!validId) return <Redirect href="/libraries/preparations" />;
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !detail) return <LoadingState label="Abriendo la información…" />;

  const states = detail && !detail.is_draft
    ? [...new Set(detail.ingredients.flatMap((ingredient) => "preparation_state" in ingredient && ingredient.preparation_state !== "unknown" ? [preparationStateLabel(ingredient.preparation_state)] : []))].join(", ") || "Sin datos declarados"
    : "Sin datos declarados";
  const portion = detail && !detail.is_draft
    ? detail.selection_mode === "units"
      ? `${formatPreparationNumber(detail.selected_units ?? 1)} ${detail.household_label} · ${formatPreparationNumber(detail.grams)} g`
      : `${formatPreparationNumber(detail.grams)} g`
    : "Sin definir";

  return <Screen headerMode="preserve">
    {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
    {detail ? <ContentPanel muted title="Información de la preparación">
      <InformationRow label="Nombre" value={detail.name} />
      {detail.is_draft ? <InformationRow label="Estado" value="Borrador" /> : <>
        <InformationRow label="Porción seleccionada" value={portion} />
        <InformationRow label="Porción habitual" value={`${formatPreparationNumber(detail.default_portion_g)} g`} />
        <InformationRow label="Rendimiento final" value={`${formatPreparationNumber(detail.yield_g)} g${detail.yield_is_manual ? " · Ajustado" : " · Estimado"}`} />
        <InformationRow label="Sodio" value={detail.nutrition.sodium_mg == null ? "Sin dato" : `${formatPreparationNumber(detail.nutrition.sodium_mg, 0)} mg`} />
        <InformationRow label="Alérgenos" value={detail.allergen_status === "unknown" ? "Sin evaluación" : formatPreparationAllergens(detail.allergens)} />
        <InformationRow label="Estados" value={states} />
        <Text style={styles.source}>{detail.is_personal ? "Estimación personal" : "Estimación editorial"} · versión {detail.version}{detail.evidence.source_name ? ` · ${detail.evidence.source_name}` : ""}</Text>
      </>}
    </ContentPanel> : null}
  </Screen>;
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  label: { color: tokens.color.textMuted, flex: 1, fontSize: tokens.type.caption },
  value: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, textAlign: "right" },
  source: { color: tokens.color.textSoft, fontSize: tokens.type.caption, lineHeight: 18 },
});
