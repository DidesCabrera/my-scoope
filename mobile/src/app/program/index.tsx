import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useMemo, useRef, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ActiveProgramData, CalendarizationHistoryData, CalendarizationStatus } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarizedProgramPlanning } from "@/components/calendarization/calendarized-program-planning";
import { ProgramWeekTabs } from "@/components/libraries/program-planning-controls";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ProgramActiveOverview } from "@/components/programs/program-active-card";
import { ConfirmationState, EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { SectionDivider, SectionHeading } from "@/components/ui";
import { Button, Card, LoadingState, Pill, Screen, SectionTitle, textStyles } from "@/components/ui/primitives";
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

function localDate(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
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
  const [weekSelection, setWeekSelection] = useState<{ calendarizationId: number; week: number } | null>(null);
  const [weekTabsPinned, setWeekTabsPinned] = useState(false);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const weekTabsOffset = useRef(Number.POSITIVE_INFINITY);
  const setHeaderPresentation = useHeaderPresentation();

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
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ mode: "default", identityVisible: compactHeaderVisible });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, setHeaderPresentation]));

  const calendarization = program?.calendarization ?? null;
  const programDays = useMemo(() => program?.days ?? [], [program]);
  const observedWeeks = useMemo(() => [...new Set(programDays.map((day) => day.week_number))], [programDays]);
  const weekCount = Math.max(program?.weeks_count ?? 0, observedWeeks.length);
  const weeks = useMemo(() => Array.from({ length: weekCount }, (_, index) => index + 1), [weekCount]);
  const preferredWeek = useMemo(() => {
    const today = localDate();
    return programDays.find((day) => day.calendar_date === today)?.week_number
      ?? programDays.find((day) => day.calendar_date > today)?.week_number
      ?? programDays.at(-1)?.week_number
      ?? weeks[0]
      ?? 1;
  }, [programDays, weeks]);

  const selectedWeek = weekSelection
    && weekSelection.calendarizationId === calendarization?.id
    && weeks.includes(weekSelection.week)
    ? weekSelection.week
    : null;
  const activeWeek = selectedWeek ?? preferredWeek;

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !program) return <LoadingState label="Preparando tu programa…" />;

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

  const historyContent = history.items.length ? history.items.map((item) => (
    <Card key={item.id} muted>
      <View style={styles.row}>
        <View style={styles.copy}><Text style={styles.historyName}>{item.program_name}</Text><Text style={textStyles.caption}>{displayDate(item.start_date)} – {displayDate(item.end_date)} · {item.days_with_plan}/{item.days_total} días con plan</Text></View>
        <Pill color={tokens.color.textSoft} label={statusLabels[item.status]} />
      </View>
    </Card>
  )) : <Text style={textStyles.muted}>Tus programas finalizados o cancelados aparecerán aquí.</Text>;

  if (!calendarization || !program) {
    return (
      <Screen>
        {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
        <EmptyState actionLabel="Calendarizar un programa" message="Elige uno de tus programas guardados para comenzar un recorrido diario." onAction={() => router.push("/program/activate" as Href)} title="Aún no tienes un programa activo" />
        <SectionTitle detail={`${history.count}`} title="Historial" />
        {historyContent}
      </Screen>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={styles.screenContent}
      keyboardShouldPersistTaps="handled"
      onScroll={({ nativeEvent }) => {
        const visible = nativeEvent.contentOffset.y > 1;
        if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible);
        const pinned = nativeEvent.contentOffset.y >= weekTabsOffset.current;
        if (pinned !== weekTabsPinned) setWeekTabsPinned(pinned);
      }}
      scrollEventThrottle={16}
      stickyHeaderIndices={[1]}
      style={styles.screen}>
      <View style={styles.beforePlanning}>
        {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
        <ProgramActiveOverview calendarization={calendarization} program={program} />
        <SectionDivider />
        <SectionHeading detail={`${weekCount} ${weekCount === 1 ? "semana" : "semanas"}`} title="Planificación Semanal" />
      </View>

      <View
        onLayout={({ nativeEvent }) => { weekTabsOffset.current = nativeEvent.layout.y; }}
        style={[styles.weekTabsSticky, weekTabsPinned && styles.weekTabsStickyPinned]}>
        <ProgramWeekTabs activeWeek={activeWeek} onChange={(week) => setWeekSelection({ calendarizationId: calendarization.id, week })} weeks={weeks} />
      </View>

      <CalendarizedProgramPlanning days={programDays} initialWeek={activeWeek} key={`${calendarization.id}:${activeWeek}`} showWeekTabs={false} weeksData={program.weeks} />

      <View style={styles.afterPlanning}>
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
        <Button label="Cambiar de programa" onPress={() => router.push("/program/activate" as Href)} variant="secondary" />
        <SectionTitle detail={`${history.count}`} title="Historial" />
        {historyContent}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  actions: { gap: tokens.spacing.sm },
  afterPlanning: { gap: tokens.spacing.lg, paddingTop: tokens.spacing.lg },
  beforePlanning: { gap: tokens.spacing.lg },
  copy: { flex: 1, gap: 4 },
  historyName: { color: tokens.color.textMain, fontSize: 16, fontWeight: "800" },
  row: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  screenContent: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  weekTabsSticky: { backgroundColor: tokens.color.surfaceApp, borderBottomColor: "transparent", borderBottomWidth: 1, marginHorizontal: -tokens.spacing.screen, paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.sm, zIndex: 2 },
  weekTabsStickyPinned: { borderBottomColor: tokens.color.borderDefault },
});
