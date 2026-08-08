import { Redirect, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarizationRevision, TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, InlineNotice, LoadingState, Pill, Screen, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

export default function RevisionScreen() {
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [revision, setRevision] = useState<CalendarizationRevision | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void apiRequest<TodayData>("/api/v1/today")
      .then((today) => setRevision(today.pending_revision))
      .catch((nextError) => setError(userFacingError(nextError)))
      .finally(() => setLoading(false));
  }, [apiRequest]);

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Preparando el ajuste…" />;

  async function decide(decision: "approve" | "reject") {
    if (!revision) return;
    setSaving(true);
    setError(null);
    try {
      setRevision(await apiRequest<CalendarizationRevision>(`/api/v1/program/revisions/${revision.id}/decision`, {
        method: "POST",
        body: JSON.stringify({ decision }),
      }));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Screen>
      <AppHeader eyebrow="Ajuste prospectivo" title="Revisa antes de cambiar" />
      <InlineNotice tone="warning">El pasado y el día actual no se modifican. Sólo se aplicarán las fechas futuras que ves aquí.</InlineNotice>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {revision ? (
        <>
          <Card accent={revision.status === "pending" ? tokens.color.warning : tokens.color.success}>
            <View style={styles.header}>
              <Text style={styles.title}>Desde {revision.effective_from}</Text>
              <Pill color={revision.status === "pending" ? tokens.color.warning : tokens.color.success} label={revision.status} />
            </View>
            <Text style={textStyles.muted}>{revision.rationale}</Text>
          </Card>
          {revision.days.map((day) => (
            <Card key={day.calendar_date} muted>
              <Text style={styles.date}>{day.calendar_date}</Text>
              <View style={styles.comparison}>
                <View style={styles.side}>
                  <Text style={textStyles.caption}>Actual</Text>
                  <Text style={styles.planName}>{day.before_name || "Plan actual"}</Text>
                  <Text style={textStyles.muted}>{Math.round(day.before_totals.total_kcal ?? 0)} kcal</Text>
                </View>
                <Text style={styles.arrow}>→</Text>
                <View style={styles.side}>
                  <Text style={textStyles.caption}>Propuesto</Text>
                  <Text style={styles.planName}>{day.after_name || "Plan propuesto"}</Text>
                  <Text style={textStyles.muted}>{Math.round(day.after_totals.total_kcal ?? 0)} kcal</Text>
                </View>
              </View>
            </Card>
          ))}
          {revision.status === "pending" ? (
            <>
              <Button label="Aprobar fechas futuras" loading={saving} onPress={() => void decide("approve")} />
              <Button disabled={saving} label="Rechazar ajuste" onPress={() => void decide("reject")} variant="danger" />
            </>
          ) : (
            <InlineNotice>{revision.status === "applied" ? "Ajuste aplicado y recordatorios futuros recalculados." : "Ajuste rechazado; el programa continúa sin cambios."}</InlineNotice>
          )}
        </>
      ) : (
        <Card><Text style={textStyles.muted}>No tienes ajustes pendientes de revisión.</Text></Card>
      )}
      <Button label="Volver a Today" onPress={() => router.back()} variant="secondary" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  title: { color: tokens.color.textMain, fontSize: 20, fontWeight: "800" },
  date: { color: tokens.color.dailyPlan, fontSize: 12, fontWeight: "900" },
  comparison: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  side: { flex: 1, gap: 4 },
  planName: { color: tokens.color.textMain, fontSize: 15, fontWeight: "800" },
  arrow: { color: tokens.color.warning, fontSize: 22, fontWeight: "900" },
});
