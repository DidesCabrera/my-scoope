import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ActiveProgramData, CalendarizationHistoryData, CalendarizationStatus } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { ConfirmationState, EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { AppHeader, Button, Card, LoadingState, Pill, ProgressBar, Screen, SectionTitle, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

type PendingAction = "pause" | "cancel" | null;

const statusLabels: Record<CalendarizationStatus, string> = {
  active: "Activo",
  cancelled: "Cancelado",
  completed: "Completado",
  paused: "Pausado",
  scheduled: "Programado",
};

function displayDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short" }).format(new Date(`${value}T12:00:00`));
}

export default function ProgramScreen() {
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [program, setProgram] = useState<ActiveProgramData | null>(null);
  const [history, setHistory] = useState<CalendarizationHistoryData>({ items: [], count: 0 });
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextProgram, nextHistory] = await Promise.all([
        apiRequest<ActiveProgramData>("/api/v1/program/active"),
        apiRequest<CalendarizationHistoryData>("/api/v1/program/calendarizations/history"),
      ]);
      setProgram(nextProgram);
      setHistory(nextHistory);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !program) return <LoadingState label="Preparando tu programa…" />;

  const calendarization = program?.calendarization ?? null;

  async function applyAction(action: "pause" | "resume" | "cancel") {
    if (!calendarization) return;
    setActing(true);
    setError(null);
    try {
      await apiRequest<ActiveProgramData>(`/api/v1/program/calendarizations/${calendarization.id}/${action}`, { method: "POST" });
      setPendingAction(null);
      await load();
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setActing(false);
    }
  }

  return (
    <Screen>
      <AppHeader eyebrow="Programa vivido" title="Mi programa" />
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {calendarization ? (
        <>
          <Card accent={tokens.color.program}>
            <View style={styles.row}>
              <View style={styles.copy}>
                <Text style={styles.name}>{calendarization.program_name}</Text>
                <Text style={textStyles.caption}>{displayDate(calendarization.start_date)} – {displayDate(calendarization.end_date)}</Text>
              </View>
              <Pill color={tokens.color.program} label={statusLabels[calendarization.status]} />
            </View>
            <Text style={textStyles.strong}>Día {calendarization.progress_day} de {calendarization.progress_total_days}</Text>
            <ProgressBar value={calendarization.progress_percent} />
            <Text style={textStyles.caption}>{calendarization.progress_percent}% del recorrido</Text>
          </Card>
          <Button label="Abrir plan de hoy" onPress={() => router.push("/today" as Href)} />

          <SectionTitle detail={`${program?.days.length ?? 0} días`} title="Recorrido" />
          <Card muted>
            {program?.days.map((day) => (
              <Pressable
                accessibilityLabel={`${displayDate(day.calendar_date)}: ${day.has_plan ? day.plan_name || "Plan diario" : "Día sin plan"}`}
                accessibilityRole="button"
                key={day.id}
                onPress={() => router.push(`/program/days/${day.id}` as Href)}
                style={({ pressed }) => [styles.day, pressed && styles.pressed]}>
                <View style={styles.dayDate}>
                  <Text style={styles.dayNumber}>{displayDate(day.calendar_date)}</Text>
                  <Text style={textStyles.caption}>S{day.week_number} · D{day.day_number}</Text>
                </View>
                <View style={styles.dayCopy}>
                  <Text numberOfLines={1} style={styles.dayName}>{day.has_plan ? day.plan_name || "Plan diario" : "Día sin plan"}</Text>
                  <Text style={textStyles.caption}>{day.has_plan ? "Ver detalle" : "Sin contenido asignado"}</Text>
                </View>
                <Text style={styles.chevron}>›</Text>
              </Pressable>
            ))}
          </Card>

          {pendingAction === "pause" ? (
            <ConfirmationState busy={acting} confirmLabel="Pausar" message="Tu progreso se conservará y podrás reanudar este programa más adelante." onCancel={() => setPendingAction(null)} onConfirm={() => void applyAction("pause")} title="¿Pausar el programa?" />
          ) : pendingAction === "cancel" ? (
            <ConfirmationState busy={acting} confirmLabel="Cancelar programa" danger message="El programa saldrá de tu recorrido actual y quedará disponible en el historial." onCancel={() => setPendingAction(null)} onConfirm={() => void applyAction("cancel")} title="¿Cancelar este programa?" />
          ) : (
            <View style={styles.actions}>
              {calendarization.status === "paused" ? <Button label="Reanudar programa" loading={acting} onPress={() => void applyAction("resume")} /> : <Button label="Pausar programa" onPress={() => setPendingAction("pause")} variant="secondary" />}
              <Button label="Configurar recordatorios" onPress={() => router.push("/reminders")} variant="secondary" />
              <Button label="Cancelar programa" onPress={() => setPendingAction("cancel")} variant="danger" />
            </View>
          )}
        </>
      ) : (
        <EmptyState actionLabel="Calendarizar un programa" message="Elige uno de tus programas guardados para comenzar un recorrido diario." onAction={() => router.push("/program/activate" as Href)} title="Aún no tienes un programa activo" />
      )}

      {calendarization ? <Button label="Cambiar de programa" onPress={() => router.push("/program/activate" as Href)} variant="secondary" /> : null}
      <SectionTitle detail={`${history.count}`} title="Historial" />
      {history.items.length ? history.items.map((item) => (
        <Card key={item.id} muted>
          <View style={styles.row}>
            <View style={styles.copy}><Text style={styles.historyName}>{item.program_name}</Text><Text style={textStyles.caption}>{displayDate(item.start_date)} – {displayDate(item.end_date)} · {item.days_with_plan}/{item.days_total} días con plan</Text></View>
            <Pill color={tokens.color.textSoft} label={statusLabels[item.status]} />
          </View>
        </Card>
      )) : <Text style={textStyles.muted}>Tus programas finalizados o cancelados aparecerán aquí.</Text>}
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: { gap: tokens.spacing.sm },
  chevron: { color: tokens.color.textSoft, fontSize: 28 },
  copy: { flex: 1, gap: 4 },
  day: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, paddingVertical: 12 },
  dayCopy: { flex: 1, gap: 3 },
  dayDate: { gap: 3, width: 68 },
  dayName: { color: tokens.color.textMain, fontSize: 15, fontWeight: "800" },
  dayNumber: { color: tokens.color.program, fontSize: 13, fontWeight: "900", textTransform: "uppercase" },
  historyName: { color: tokens.color.textMain, fontSize: 16, fontWeight: "800" },
  name: { color: tokens.color.textMain, fontSize: 22, fontWeight: "900" },
  pressed: { opacity: 0.6 },
  row: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
});
