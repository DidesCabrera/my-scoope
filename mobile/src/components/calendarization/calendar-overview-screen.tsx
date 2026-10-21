import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { CalendarDays, ChevronLeft, ChevronRight, Ellipsis, RotateCcw } from "lucide-react-native";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarDay, CalendarDayDetailData, CalendarOverviewData, CalendarProgressData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarizedDailyPlanCard } from "@/components/calendarization/calendarized-daily-plan-card";
import { CalendarPlanEditor } from "@/components/calendarization/calendar-plan-editor";
import { monthKeyFromDate, monthLabel, monthWindow, shiftMonth } from "@/components/calendarization/calendar-month";
import { ProgramDaySelector } from "@/components/libraries/program-planning-controls";
import { ProgramSectionHeader } from "@/components/programs/program-section-header";
import { ProgramActiveKpis } from "@/components/programs/program-active-kpis";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
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

function inclusiveDays(start: string, end: string): number {
  const toUtc = (value: string) => Date.UTC(Number(value.slice(0, 4)), Number(value.slice(5, 7)) - 1, Number(value.slice(8, 10)));
  return Math.max(1, Math.round((toUtc(end) - toUtc(start)) / 86_400_000) + 1);
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
  const [visibleMonth, setVisibleMonth] = useState<string | null>(null);
  const [monthOverview, setMonthOverview] = useState<{ key: string; revision: number; data: CalendarOverviewData } | null>(null);
  const [monthError, setMonthError] = useState<string | null>(null);
  const [monthRevision, setMonthRevision] = useState(0);
  const [detail, setDetail] = useState<CalendarDayDetailData | null>(null);
  const [progress, setProgress] = useState<CalendarProgressData | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingDate, setEditingDate] = useState<string | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const [progressMenuVisible, setProgressMenuVisible] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);
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
      setVisibleMonth((previous) => previous ?? monthKeyFromDate(nextOverview.local_date));
      setSelectedDate((previous) => previous && nextOverview.days.some((day) => day.calendar_date === previous)
        ? previous : nextOverview.local_date);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, extended]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    if (status !== "authenticated" || !visibleMonth || extended) return;
    let active = true;
    const window = monthWindow(visibleMonth);
    setMonthError(null);
    void apiRequest<CalendarOverviewData>(`/api/v1/calendar?start_date=${window.startDate}&days=${window.days}`)
      .then((data) => { if (active) setMonthOverview({ key: visibleMonth, revision: monthRevision, data }); })
      .catch((nextError) => { if (active) setMonthError(userFacingError(nextError)); });
    return () => { active = false; };
  }, [apiRequest, extended, monthRevision, status, visibleMonth]));
  useEffect(() => {
    if (!selectedDate || status !== "authenticated") return;
    let active = true;
    void apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${selectedDate}`)
      .then((next) => { if (active) setDetail(next); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
    return () => { active = false; };
  }, [apiRequest, selectedDate, status]);

  const week = useMemo(() => overview?.days.slice(0, 7) ?? [], [overview]);
  const monthDays = monthOverview?.key === visibleMonth && monthOverview.revision === monthRevision ? monthOverview.data.days : [];
  const upcoming = useMemo(() => {
    if (!overview) return [];
    if (extended) return overview.days;
    const future = overview.days.filter((day) => day.calendar_date >= overview.local_date);
    return future.slice(0, 7);
  }, [extended, overview]);
  const selectedDetail = detail?.calendar_date === selectedDate ? detail : null;
  const editorDay = monthDays.find((day) => day.calendar_date === editingDate)
    ?? overview?.days.find((day) => day.calendar_date === editingDate);
  const elapsedCalendarDays = progress ? inclusiveDays(progress.period_start, progress.period_end) : 0;
  const calendarCoverage = progress ? Math.round(progress.days_with_plan / elapsedCalendarDays * 100) : 0;
  const canResetProgress = Boolean(progress && overview && progress.period_start < overview.local_date);
  async function resetProgress() {
    setResetBusy(true);
    setResetError(null);
    try {
      await apiRequest<CalendarProgressData>("/api/v1/calendar/progress/periods", { body: "{}", method: "POST" });
      await load();
      setConfirmReset(false);
      setProgressMenuVisible(false);
    } catch (nextError) {
      setResetError(userFacingError(nextError));
    } finally {
      setResetBusy(false);
    }
  }
  function closeProgressMenu() {
    if (resetBusy) return;
    setProgressMenuVisible(false);
    setConfirmReset(false);
    setResetError(null);
  }
  async function refreshCalendar() {
    await load();
    setMonthRevision((previous) => previous + 1);
  }
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !overview) return <LoadingState label="Preparando tu calendario…" />;

  return (
    <>
    <Screen contentStyle={styles.content}>
      <SectionPageHeader countLabel="fechas" section="calendarization" subtitle={extended ? undefined : "Trae tus planes y programas al calendario, y ejecútalos registrando su cumplimiento"} title={extended ? "Próximas fechas" : "Calendario"} />
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {!extended ? <View style={styles.summaryRow}>
        <View accessibilityLabel={`Planes programados desde hoy: ${overview?.future_plans_count ?? "dato pendiente"}`} accessible style={styles.summaryCard}>
          <Text style={styles.summaryLabel}>Planes programados</Text>
          <Text style={styles.summaryValue}>{overview?.future_plans_count ?? "—"}</Text>
          <Text style={styles.summaryHint}>Desde hoy</Text>
        </View>
        <View accessibilityLabel={`Última fecha con plan: ${overview?.last_scheduled_date === undefined ? "dato pendiente" : overview.last_scheduled_date ?? "sin fecha"}`} accessible style={styles.summaryCard}>
          <Text style={styles.summaryLabel}>Última fecha con plan</Text>
          <Text style={styles.summaryDateValue}>{overview?.last_scheduled_date === undefined ? "—" : overview.last_scheduled_date ? dateLabel(overview.last_scheduled_date, { day: "numeric", month: "short", year: "numeric" }) : "Sin fecha"}</Text>
          <Text style={styles.summaryHint}>Horizonte programado</Text>
        </View>
      </View> : null}
      {!extended ? (
        <>
          <Card>
            <View style={styles.monthNavigation}>
              <Pressable accessibilityLabel="Mes anterior" accessibilityRole="button" onPress={() => setVisibleMonth((current) => current ? shiftMonth(current, -1) : current)} style={styles.monthArrow}>
                <ChevronLeft color={tokens.color.textMain} size={20} />
              </Pressable>
              <Text accessibilityRole="header" style={styles.monthTitle}>{visibleMonth ? monthLabel(visibleMonth) : ""}</Text>
              <Pressable accessibilityLabel="Mes siguiente" accessibilityRole="button" onPress={() => setVisibleMonth((current) => current ? shiftMonth(current, 1) : current)} style={styles.monthArrow}>
                <ChevronRight color={tokens.color.textMain} size={20} />
              </Pressable>
            </View>
            {visibleMonth && overview && visibleMonth !== monthKeyFromDate(overview.local_date) ? <Pressable accessibilityRole="button" onPress={() => setVisibleMonth(monthKeyFromDate(overview.local_date))}><Text style={styles.monthTodayLink}>Volver al mes actual</Text></Pressable> : null}
            {monthError ? <InlineNotice tone="error">{monthError}</InlineNotice> : null}
            {!monthDays.length && !monthError ? <LoadingState label="Cargando mes…" /> : null}
            <View style={styles.grid}>
              {(["L", "M", "M", "J", "V", "S", "D"] as const).map((label, index) => <Text key={`weekday-${index}`} style={styles.gridHeader}>{label}</Text>)}
              {monthDays.map((day) => (
                <Pressable
                  accessibilityLabel={`${dateLabel(day.calendar_date, { day: "numeric", month: "long", year: "numeric" })}: ${day.has_plan ? "Con plan" : "Sin plan"}`}
                  accessibilityRole="button"
                  key={day.calendar_date}
                  onPress={() => setEditingDate(day.calendar_date)}
                  style={[styles.gridDate, day.has_plan && styles.gridDateFilled, monthKeyFromDate(day.calendar_date) !== visibleMonth && styles.gridDateAdjacent, day.calendar_date === overview?.local_date && styles.gridDateToday]}>
                  <Text style={[styles.gridNumber, day.has_plan && styles.gridNumberWithPlan]}>{day.calendar_date.slice(8, 10)}</Text>
                </Pressable>
              ))}
            </View>
          </Card>

          {progress ? <>
            <ProgramSectionHeader
              action={<Pressable accessibilityLabel="Opciones de progreso" accessibilityRole="button" onPress={() => setProgressMenuVisible(true)} style={styles.progressMenuButton}><Ellipsis color={tokens.color.textMain} size={24} /></Pressable>}
              icon={CalendarDays}
              subtitle={`Desde el ${dateLabel(progress.period_start, { day: "numeric", month: "long" })}`}
              title="Progreso"
            />
            <ProgramActiveKpis
              adheredDays={progress.completed_meals}
              adherence={progress.adherence_percent}
              bleed={false}
              elapsedDays={progress.days_with_plan}
              planLabel="Días con plan"
              plannedAdherenceDays={progress.elapsed_meals}
              progress={calendarCoverage}
              standalone
              totalDays={elapsedCalendarDays}
            />
          </> : null}

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

        </>
      ) : null}

      <ProgramSectionHeader icon={CalendarDays} subtitle={extended ? "Planes ordenados por fecha." : "Los próximos siete días, con el nombre de cada plan."} title="Próximas fechas" />
      <Card>
        {upcoming.map((day) => <CalendarDateRow day={day} key={day.calendar_date} onEdit={() => setEditingDate(day.calendar_date)} onPress={day.id
          ? () => router.push(`/program/days/${day.id}` as Href) : undefined} />)}
      </Card>
      {!extended ? <Button label="Ver más fechas" onPress={() => router.push("/calendar/future" as Href)} variant="secondary" /> : null}
      {!extended ? <Button label="Planificar con un programa" onPress={() => router.push("/program" as Href)} variant="secondary" /> : null}
    </Screen>
    <ActionSheetModal onRequestClose={closeProgressMenu} visible={progressMenuVisible}>
      <SafeAreaView edges={["left", "right"]} style={styles.progressSheet}>
        <ActionSheetHeader icon={CalendarDays} onClose={closeProgressMenu} title={confirmReset ? "Reiniciar periodo" : "Progreso"} />
        <ScrollView contentContainerStyle={styles.progressSheetContent} showsVerticalScrollIndicator={false}>
          {resetError ? <InlineNotice tone="error">{resetError}</InlineNotice> : null}
          {confirmReset ? <ConfirmationState busy={resetBusy} confirmLabel="Reiniciar periodo de progreso" message="El nuevo periodo comenzará hoy. Tus registros y periodos anteriores se conservarán." onCancel={() => setConfirmReset(false)} onConfirm={() => void resetProgress()} title="¿Reiniciar el periodo de progreso?" /> : <>
            <ActionSheetActions>
              <ActionSheetAction disabled={!canResetProgress} icon={RotateCcw} label="Reiniciar periodo de progreso" onPress={() => setConfirmReset(true)} />
            </ActionSheetActions>
            {!canResetProgress ? <InlineNotice>Este periodo comenzó hoy. Podrás reiniciarlo a partir de mañana.</InlineNotice> : null}
          </>}
        </ScrollView>
      </SafeAreaView>
    </ActionSheetModal>
    <Modal animationType="slide" onRequestClose={() => setEditingDate(null)} visible={Boolean(editorDay)}>
      <SafeAreaView style={styles.editorSafeArea}>
        <ScrollView contentContainerStyle={styles.editorContent} showsVerticalScrollIndicator={false}>
          {editorDay && overview ? <CalendarPlanEditor apiRequest={apiRequest} day={editorDay} key={editorDay.calendar_date} localToday={overview.local_date} onChanged={refreshCalendar} onClose={() => setEditingDate(null)} /> : null}
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
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: tokens.spacing.sm },
  gridDate: { alignItems: "center", borderColor: "transparent", borderRadius: 10, borderWidth: 2, justifyContent: "center", minHeight: 38, width: "13.5%" },
  gridDateAdjacent: { opacity: 0.5 },
  gridDateFilled: { backgroundColor: `${tokens.color.dailyPlan}33` },
  gridDateToday: { borderColor: tokens.color.success },
  gridHeader: { color: tokens.color.textMuted, fontSize: 11, textAlign: "center", width: "13.5%" },
  gridNumber: { color: tokens.color.textMain, fontSize: 14, fontWeight: "500" },
  gridNumberWithPlan: { color: tokens.color.dailyPlan, fontWeight: "700" },
  monthArrow: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: 10, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  monthNavigation: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: tokens.spacing.md },
  monthTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: "600" },
  monthTodayLink: { color: tokens.color.interactivePrimary, fontSize: 13, marginBottom: tokens.spacing.sm, textAlign: "center" },
  progressMenuButton: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: 18, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  progressSheet: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  progressSheetContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  summaryCard: { backgroundColor: tokens.color.surfaceCard, borderRadius: tokens.radius.panel, flex: 1, gap: tokens.spacing.xs, justifyContent: "space-between", minHeight: 122, padding: tokens.spacing.md },
  summaryDateValue: { color: tokens.color.textMain, fontSize: 20, fontWeight: "700" },
  summaryHint: { color: tokens.color.textMuted, fontSize: 12 },
  summaryLabel: { color: tokens.color.textMain, fontSize: 14, fontWeight: "600" },
  summaryRow: { flexDirection: "row", gap: tokens.spacing.sm },
  summaryValue: { color: tokens.color.textMain, fontSize: 32, fontWeight: "700", fontVariant: ["tabular-nums"] },
  pressed: { opacity: 0.65 },
});
