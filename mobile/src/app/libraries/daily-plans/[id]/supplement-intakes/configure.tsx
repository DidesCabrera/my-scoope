import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import { Alert, ScrollView, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { SupplementIntakePreset } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { SupplementIntakePresetCard } from "@/components/supplements/supplement-intake-preset-card";
import { Button, Card, InlineNotice, LoadingState, NativeDateTimeField } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { internalHref } from "@/navigation/internal-href";

export default function ConfigureSupplementIntakeScreen() {
  const { calendarizedDayId, id, pinned, presetId, returnTo } = useLocalSearchParams<{ calendarizedDayId?: string; id: string; pinned?: string; presetId?: string; returnTo?: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [item, setItem] = useState<SupplementIntakePreset | null>(null);
  const [hour, setHour] = useState("08:00");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const returnHref = internalHref(returnTo) ?? `/libraries/daily-plans/${id}` as Href;
  const selectionHref = useMemo(() => ({
    pathname: "/libraries/daily-plans/[id]/supplement-intakes/add" as const,
    params: {
      id,
      returnTo: String(returnHref),
      ...(calendarizedDayId ? { calendarizedDayId } : {}),
      ...(pinned === "1" ? { pinned: "1" } : {}),
    },
  }), [calendarizedDayId, id, pinned, returnHref]);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: selectionHref, forceFallback: true, mode: "back", title: "Configurar ingesta" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [selectionHref, setHeaderPresentation]));
  useFocusEffect(useCallback(() => {
    let active = true;
    setLoading(true); setError(null);
    void apiRequest<SupplementIntakePreset>(`/api/v1/library/supplement-intake-presets/${presetId}`)
      .then((result) => { if (active) setItem(result); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, presetId]));

  async function add() {
    if (!item || saving) return;
    if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(hour)) { setError("Ingresa una hora válida entre 00:00 y 23:59."); return; }
    setSaving(true); setError(null);
    try {
      const endpoint = calendarizedDayId
        ? `/api/v1/days/${calendarizedDayId}/supplement-intakes/from-preset`
        : `/api/v1/library/daily-plans/${id}/supplement-intakes/from-preset`;
      await apiRequest(endpoint, {
        method: "POST",
        body: JSON.stringify({ preset_id: item.id, hour }),
      });
      Alert.alert("Listo", `${item.name} fue agregada a la minuta.`, [{ text: "Aceptar", onPress: () => router.dismissTo(returnHref) }]);
    } catch (nextError) { setError(userFacingError(nextError)); }
    finally { setSaving(false); }
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !item) return <LoadingState label="Preparando la ingesta…" />;
  return <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
    <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      <Card style={styles.timeCard}>
        <NativeDateTimeField
          confirmationColor={tokens.color.supplement}
          containerStyle={styles.compactControlField}
          iconColor={tokens.color.textMain}
          iconInLabel
          initiallyExpanded
          inlineLabel
          inputStyle={styles.timeValue}
          label="Hora de la ingesta"
          labelStyle={styles.timeLabel}
          minuteInterval={5}
          mode="time"
          onChange={setHour}
          value={hour}
        />
      </Card>
      {item ? <SupplementIntakePresetCard contained item={item} /> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      <View style={styles.action}><Button disabled={!item || saving} label="Agregar ingesta" loading={saving} onPress={() => void add()} variant="primary" /></View>
    </ScrollView>
  </SafeAreaView>;
}

const styles = StyleSheet.create({
  action: { marginTop: tokens.spacing.sm },
  compactControlField: { borderRadius: tokens.radius.md, marginHorizontal: 0, marginRight: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 36, width: 120 },
  content: { flexGrow: 1, gap: tokens.spacing.lg, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  safeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  timeCard: { borderRadius: 18, minHeight: 52, paddingVertical: 6 },
  timeLabel: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  timeValue: { textAlign: "center" },
});
