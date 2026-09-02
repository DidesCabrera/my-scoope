import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import { ScrollView, StyleSheet, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ActiveProgramData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarizedProgramPlanning } from "@/components/calendarization/calendarized-program-planning";
import { ProgramWeekTabs } from "@/components/libraries/program-planning-controls";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ProgramActiveActions } from "@/components/programs/program-active-actions";
import { ProgramActiveOverview } from "@/components/programs/program-active-card";
import { EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { LoadingState, Screen, SectionDivider, SectionHeading, SectionPageHeader } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { refreshNativeReminders } from "@/notifications/native-reminders";

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionsVisible, setActionsVisible] = useState(false);
  const [weekSelection, setWeekSelection] = useState<{ calendarizationId: number; week: number } | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const setHeaderPresentation = useHeaderPresentation();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setProgram(await apiRequest<ActiveProgramData>("/api/v1/program/active"));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  const openActions = useCallback(() => setActionsVisible(true), []);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      action: loading && !program ? undefined : { label: "Acciones del programa en curso", onPress: openActions },
      identityVisible: compactHeaderVisible,
      mode: "default",
      title: "Mi programa",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, loading, openActions, program, setHeaderPresentation]));

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
    if (!calendarization) throw new Error("No hay un programa en curso para actualizar.");
    const nextProgram = await apiRequest<ActiveProgramData>(`/api/v1/program/calendarizations/${calendarization.id}/${action}`, { method: "POST" });
    setProgram(nextProgram);
    try {
      await refreshNativeReminders(apiRequest);
    } catch {
      setError("El programa se actualizó, pero el iPhone no pudo reconciliar sus avisos. Abre Recordatorios para reintentarlo.");
    }
  }

  const actionsModal = (
    <ProgramActiveActions
      onChangeProgram={() => router.push("/program/activate" as Href)}
      onClose={() => setActionsVisible(false)}
      onOpenHistory={() => router.push("/program/history" as Href)}
      onOpenReminders={() => router.push("/reminders")}
      onStateAction={applyAction}
      status={calendarization?.status ?? null}
      visible={actionsVisible}
    />
  );

  if (!calendarization || !program) {
    return (
      <>
        <Screen headerMode="preserve">
          <SectionPageHeader countLabel="semanas" section="calendarization" title="Mi programa" />
          {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
          <EmptyState actionLabel="Calendarizar un programa" message="Elige uno de tus programas guardados para comenzar un recorrido diario." onAction={() => router.push("/program/activate" as Href)} title="Aún no tienes un programa activo" />
        </Screen>
        {actionsModal}
      </>
    );
  }

  return (
    <>
      <ScrollView
        contentContainerStyle={styles.screenContent}
        keyboardShouldPersistTaps="handled"
        onScroll={({ nativeEvent }) => {
          const visible = nativeEvent.contentOffset.y > 1;
          if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible);
        }}
        scrollEventThrottle={16}
        stickyHeaderIndices={[1]}
        style={styles.screen}>
        <View style={styles.beforePlanning}>
          <SectionPageHeader count={weekCount} countLabel="semanas" section="calendarization" title="Mi programa" />
          {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
          <ProgramActiveOverview calendarization={calendarization} program={program} />
          <SectionDivider />
          <SectionHeading detail={`${weekCount} ${weekCount === 1 ? "semana" : "semanas"}`} title="Planificación Semanal" />
        </View>

        <View style={styles.weekTabsSticky}>
          <ProgramWeekTabs activeWeek={activeWeek} onChange={(week) => setWeekSelection({ calendarizationId: calendarization.id, week })} weeks={weeks} />
        </View>

        <CalendarizedProgramPlanning days={programDays} initialWeek={activeWeek} key={`${calendarization.id}:${activeWeek}`} showWeekTabs={false} weeksData={program.weeks} />
      </ScrollView>
      {actionsModal}
    </>
  );
}

const styles = StyleSheet.create({
  beforePlanning: { gap: tokens.spacing.lg },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  screenContent: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  weekTabsSticky: { backgroundColor: tokens.color.surfaceApp, marginHorizontal: -tokens.spacing.screen, paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.sm, zIndex: 2 },
});
