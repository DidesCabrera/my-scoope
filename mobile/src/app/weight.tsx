import { Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { WeightInput, WeightItem, WeightListData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, Field, InlineNotice, LoadingState, Screen, SectionTitle, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(
    new Date(`${value}T12:00:00`),
  );
}

export default function WeightScreen() {
  const router = useRouter();
  const { status, profile, apiRequest, refreshProfile } = useSession();
  const [items, setItems] = useState<WeightItem[]>([]);
  const [value, setValue] = useState(profile?.current_weight_kg?.toString() ?? "");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const history = await apiRequest<WeightListData>("/api/v1/weights?limit=12");
      setItems(history.items);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !items.length) return <LoadingState label="Cargando tus mediciones…" />;

  async function save() {
    const weight = Number(value.replace(",", "."));
    if (!Number.isFinite(weight) || weight < 25 || weight > 350) {
      setError("Ingresa un peso válido entre 25 y 350 kg.");
      return;
    }
    const payload: WeightInput = { weight_kg: weight };
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      await apiRequest<WeightItem>("/api/v1/weights", { method: "POST", body: JSON.stringify(payload) });
      await Promise.all([load(), refreshProfile()]);
      setSaved(true);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Screen>
      <AppHeader eyebrow="Mediciones" title="Registra tu peso" />
      <Card accent={tokens.color.protein}>
        <Text style={textStyles.muted}>Mídete en condiciones similares para que la tendencia sea comparable. Una cifra aislada no define tu progreso.</Text>
        <Field keyboardType="decimal-pad" label="Peso actual (kg)" onChangeText={setValue} placeholder="82.5" value={value} />
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        {saved ? <InlineNotice>Medición guardada. Tu Today ya usa el peso actualizado.</InlineNotice> : null}
        <Button label="Guardar medición" loading={saving} onPress={save} />
      </Card>
      <SectionTitle detail={`${items.length} registros`} title="Historial reciente" />
      <Card muted>
        {items.length ? items.map((item, index) => (
          <View key={item.id} style={[styles.weightRow, index < items.length - 1 && styles.weightRowBorder]}>
            <View>
              <Text style={styles.weightValue}>{item.weight_kg.toFixed(1)} kg</Text>
              <Text style={textStyles.caption}>{formatDate(item.measured_on)}</Text>
            </View>
            <Text style={styles.source}>{item.source === "onboarding" ? "Inicio" : "Manual"}</Text>
          </View>
        )) : <Text style={textStyles.muted}>Tu primera medición aparecerá aquí.</Text>}
      </Card>
      <Button label="Volver a Today" onPress={() => router.back()} variant="secondary" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  weightRow: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", paddingVertical: 11 },
  weightRowBorder: { borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1 },
  weightValue: { color: tokens.color.textMain, fontSize: 18, fontWeight: "800", fontVariant: ["tabular-nums"] },
  source: { color: tokens.color.textSoft, fontSize: 12, fontWeight: "700", textTransform: "uppercase" },
});
