import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { CalendarDays, ChevronRight } from "lucide-react-native";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarDay, CalendarDayDetailData, CalendarOverviewData, CalendarProgressData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarizedDailyPlanCard } from "@/components/calendarization/calendarized-daily-plan-card";
import { CalendarPlanEditor } from "@/components/calendarization/calendar-plan-editor";
import { ProgramDaySelector } from "@/components/libraries/program-planning-controls";
import { ProgramSectionHeader } from "@/components/programs/program-section-header";
import { Button, Card, InlineNotice, LoadingState, Screen, SectionPageHeader } from "@/components/ui";
import { ConfirmationState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";

function dateLabel(value: string, options: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat("es-CL", options).format(new Date(`${value}T12:00:00`));
}

function compactDate(value: string): string {
  return dateLabel(value, { day: "numeric", month: "short" });
}

function weekDay(value: string): string {
  return dateLabel(value, { weekday: "narrow" }).toUpperCase();
}

function CalendarDateRow({ day, onEdit, onPress }: { day: CalendarDay; onEdit(): void; onPress?(): void }) {
  return (
    <View style={styles.agendaRow}>
      <View style={styles.agendaDate}>
        <Text style={styles.agendaDay}>{dateLabel(day.calendar_date, { weekday: "short" })}</Text>
        <Text style={styles.agendaNumber}>{day.calendar_date.slice(8, 10)}</Text>
      </View>
      <View style={styles.agendaPlan}>
        <Text numberOfLines={2} style={styles.agendaName}>{day.has_plan ? day.plan_name : "Sin plan asignado"}</Text>
        {day.source_program_name ? <Text style={styles.agendaSource}>{day.source_program_name}</Text> : null}
      </View>
      <Pressable accessibilityLabel={`Planificar ${compactDate(day.calendar_date)}`} accessibilityRole="button" onPress={onEdit} style={styles.agendaAction}>
        <Text style={styles.agendaActionText}>{day.has_plan ? "Editar" : "Asignar"}</Text>
      </Pressable>
      {onPress ? <Pressable accessibilityLabel={`Ver detalle de ${day.plan_name}`} accessibilityRole="button" onPress={onPress}><ChevronRight color={tokens.color.textMuted} size={18} /></Pressable> : null}
    </View>
  );
}

export function CalendarOverviewScreen({ extended = false }: { extended?: boolean }) {
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const [overview, setOverview] = useState<CalendarOverviewData | null>(null);
  const [detail, setDetail] = useState<CalendarDayDetailData | null>(null);
  const [progress, setProgress] = useState<CalendarProgressData | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingDate, setEditingDate] = useState<string | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const [resetBusy, setResetBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextOverview, nextProgress] = await Promise.all([
        apiRequest<CalendarOverviewData>(`/api/v1/calendar?days=${extended ? 42 : 35}`),
        apiRequest<CalendarProgressData>("/api/v1/calendar/progress"),
      ]);
      setOverview(nextOverview);
      setProgress(nextProgress);
      setSelectedDate((previous) => previous && nextOverview.days.some((day) => day.calendar_date === previous)
        ? previous : nextOverview.local_date);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, extended]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useEffect(() => {
    if (!selectedDate || status !== "authenticated") return;
    let active = true;
    void apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${selectedDate}`)
      .then((next) => { if (active) setDetail(next); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
    return () => { active = false; };
  }, [apiRequest, selectedDate, status]);

  const week = useMemo(() => overview?.days.slice(0, 7) ?? [], [overview]);
  const grid = useMemo(() => overview?.days.slice(7, 35) ?? [], [overview]);
  const upcoming = useMemo(() => {
    if (!overview) return [];
    if (extended) return overview.days;
    const future = overview.days.filter((day) => day.calendar_date >= overview.local_date);
    return future.slice(0, 7);
  }, [extended, overview]);
  const selectedDetail = detail?.calendar_date === selectedDate ? detail : null;
  const editorDay = overview?.days.find((day) => day.calendar_date === editingDate);
  async function resetProgress() {
    setResetBusy(true);
    setError(null);
    try {
      await apiRequest<CalendarProgressData>("/api/v1/calendar/progress/periods", { body: "{}", method: "POST" });
      setConfirmReset(false);
      await load();
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setResetBusy(false);
    }
  }
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !overview) return <LoadingState label="Preparando tu calendario…" />;

  return (
    <>
    <Screen contentStyle={styles.content}>
      <SectionPageHeader countLabel="fechas" section="calendarization" title={extended ? "Próximas fechas" : "Calendario"} />
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {!extended ? (
        <>
          <ProgramSectionHeader icon={CalendarDays} subtitle="Elige una fecha para revisar el plan que quedó programado." title="Semana actual" />
          <ProgramDaySelector
            accessibilityLabel="Fechas de la semana actual"
            allowEmptySelection
            days={week.map((day) => ({
              dayOfMonth: Number(day.calendar_date.slice(8, 10)),
              filled: day.has_plan,
              id: day.calendar_date,
              isToday: day.calendar_date === overview?.local_date,
              label: weekDay(day.calendar_date),
              monthLabel: dateLabel(day.calendar_date, { month: "short" }),
            }))}
            onSelect={(day) => { setError(null); setSelectedDate(String(day.id)); }}
            selectedId={selectedDate}>
            {!selectedDetail && !error ? <LoadingState label="Abriendo esta fecha…" /> : selectedDetail?.has_plan && selectedDetail.plan_snapshot ? (
              <CalendarizedDailyPlanCard
                apiRequest={apiRequest}
                dateLabel={compactDate(selectedDetail.calendar_date)}
                dayId={selectedDetail.id}
                eyebrow={selectedDetail.source_program_name ?? "PLAN DE CALENDARIO"}
                mealExecution={selectedDetail.meal_execution}
                onChanged={async () => { setDetail(await apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${selectedDetail.calendar_date}`)); }}
                planName={selectedDetail.plan_name}
                snapshot={selectedDetail.plan_snapshot}
              />
            ) : selectedDetail ? <InlineNotice>No hay un plan asignado a esta fecha.</InlineNotice> : null}
          </ProgramDaySelector>
          {selectedDetail && !selectedDetail.has_execution ? <Button label={selectedDetail.has_plan ? "Cambiar plan de esta fecha" : "Asignar plan a esta fecha"} onPress={() => setEditingDate(selectedDetail.calendar_date)} variant="secondary" /> : null}

          <ProgramSectionHeader icon={CalendarDays} subtitle="Cobertura de las próximas cuatro semanas." title="Próximas semanas" />
          <Card>
            <View style={styles.grid}>
              {grid.map((day) => (
                <Pressable
                  accessibilityLabel={`${compactDate(day.calendar_date)}: ${day.has_plan ? "Con plan" : "Sin plan"}`}
                  accessibilityRole="button"
                  key={day.calendar_date}
                  onPress={() => setEditingDate(day.calendar_date)}
                  style={[styles.gridDate, day.has_plan && styles.gridDateFilled]}>
                  <Text style={styles.gridWeekday}>{weekDay(day.calendar_date)}</Text>
                  <Text style={styles.gridNumber}>{day.calendar_date.slice(8, 10)}</Text>
                </Pressable>
              ))}
            </View>
          </Card>
        </>
      ) : null}

      <ProgramSectionHeader icon={CalendarDays} subtitle={extended ? "Planes ordenados por fecha." : "Los próximos siete días, con el nombre de cada plan."} title="Próximas fechas" />
      <Card>
        {upcoming.map((day) => <CalendarDateRow day={day} key={day.calendar_date} onEdit={() => setEditingDate(day.calendar_date)} onPress={day.id
          ? () => router.push(`/program/days/${day.id}` as Href) : undefined} />)}
      </Card>
      {!extended ? <Button label="Ver más fechas" onPress={() => router.push("/calendar/future" as Href)} variant="secondary" /> : null}
      {!extended && progress ? (
        <Card>
          <Text style={styles.progressTitle}>Cumplimiento desde {compactDate(progress.period_start)}</Text>
          <Text style={styles.progressValue}>{progress.adherence_percent}%</Text>
          <Text style={styles.progressCaption}>{progress.completed_meals} de {progress.elapsed_meals} comidas transcurridas</Text>
          {progress.period_start < (overview?.local_date ?? "") ? <Button label="Iniciar nuevo periodo de progreso" onPress={() => setConfirmReset(true)} variant="secondary" /> : null}
          {confirmReset ? <ConfirmationState busy={resetBusy} confirmLabel="Iniciar nuevo periodo" message="El contador principal comenzará hoy. Tus registros y periodos anteriores no se borrarán." onCancel={() => setConfirmReset(false)} onConfirm={() => void resetProgress()} title="¿Reiniciar el periodo de cumplimiento?" /> : null}
        </Card>
      ) : null}
      {!extended ? <Button label="Planificar con un programa" onPress={() => router.push("/program" as Href)} variant="secondary" /> : null}
    </Screen>
    <Modal animationType="slide" onRequestClose={() => setEditingDate(null)} visible={Boolean(editorDay)}>
      <SafeAreaView style={styles.editorSafeArea}>
        <ScrollView contentContainerStyle={styles.editorContent} showsVerticalScrollIndicator={false}>
          {editorDay && overview ? <CalendarPlanEditor apiRequest={apiRequest} day={editorDay} key={editorDay.calendar_date} localToday={overview.local_date} onChanged={load} onClose={() => setEditingDate(null)} /> : null}
        </ScrollView>
      </SafeAreaView>
    </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  agendaDate: { alignItems: "center", minWidth: 44 },
  agendaAction: { borderColor: tokens.color.borderSoft, borderRadius: 14, borderWidth: 1, paddingHorizontal: 8, paddingVertical: 6 },
  agendaActionText: { color: tokens.color.textMain, fontSize: 12 },
  agendaDay: { color: tokens.color.textMuted, fontSize: 12 },
  agendaName: { color: tokens.color.textMain, fontSize: 15, fontWeight: "600" },
  agendaNumber: { color: tokens.color.textMain, fontSize: 19, fontWeight: "700" },
  agendaPlan: { flex: 1, gap: 3 },
  agendaRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 68, paddingVertical: tokens.spacing.sm },
  agendaSource: { color: tokens.color.textMuted, fontSize: 12 },
  content: { gap: tokens.spacing.lg },
  editorContent: { gap: tokens.spacing.lg, padding: tokens.spacing.screen },
  editorSafeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 5 },
  gridDate: { alignItems: "center", borderColor: tokens.color.borderSoft, borderRadius: 10, borderWidth: 1, justifyContent: "center", minHeight: 49, width: "13.3%" },
  gridDateFilled: { borderColor: tokens.color.program, borderWidth: 2 },
  gridNumber: { color: tokens.color.textMain, fontSize: 15, fontWeight: "600" },
  gridWeekday: { color: tokens.color.textMuted, fontSize: 10 },
  pressed: { opacity: 0.65 },
  progressCaption: { color: tokens.color.textMuted, fontSize: 13 },
  progressTitle: { color: tokens.color.textMain, fontSize: 15, fontWeight: "600" },
  progressValue: { color: tokens.color.textMain, fontSize: 32, fontWeight: "700" },
});
