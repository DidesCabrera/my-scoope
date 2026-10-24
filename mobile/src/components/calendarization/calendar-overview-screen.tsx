import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { CalendarDays, CalendarRange, ChevronLeft, ChevronRight, Ellipsis, ListPlus } from "lucide-react-native";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarDay, CalendarDayDetailData, CalendarOverviewData, CalendarProgressData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarizedDailyPlanCard } from "@/components/calendarization/calendarized-daily-plan-card";
import { CalendarUpcomingPanels } from "@/components/calendarization/calendar-upcoming-panels";
import { commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { monthKeyFromDate, monthLabel, shiftMonth } from "@/components/calendarization/calendar-month";
import { createCalendarMonthCache } from "@/components/calendarization/calendar-month-cache";
import { ProgramDaySelector } from "@/components/libraries/program-planning-controls";
import { ProgramSectionHeader } from "@/components/programs/program-section-header";
import { ProgramActiveKpis } from "@/components/programs/program-active-kpis";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, Chip, DistributedTabBar, EntityIcon, InlineNotice, LoadingState, NativeDateTimeField, Screen, SectionPageHeader } from "@/components/ui";
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

function CalendarMonthPlaceholder() {
  return <View accessibilityLabel="Cargando días del mes" accessible style={styles.grid}>
    {(["L", "M", "M", "J", "V", "S", "D"] as const).map((label, index) => <Text key={`placeholder-weekday-${index}`} style={styles.gridHeader}>{label}</Text>)}
    {Array.from({ length: 42 }, (_, index) => <View key={`placeholder-day-${index}`} style={styles.gridPlaceholderDate}><View style={styles.gridPlaceholderNumber} /></View>)}
  </View>;
}

export function CalendarOverviewScreen({ extended = false }: { extended?: boolean }) {
  const router = useRouter();
  const { apiRequest, profile, refreshProfile, status } = useSession();
  const monthCache = useMemo(() => createCalendarMonthCache(apiRequest), [apiRequest]);
  const [overview, setOverview] = useState<CalendarOverviewData | null>(null);
  const [visibleMonth, setVisibleMonth] = useState<string | null>(null);
  const [monthOverview, setMonthOverview] = useState<{ key: string; data: CalendarOverviewData } | null>(null);
  const [monthError, setMonthError] = useState<string | null>(null);
  const [detail, setDetail] = useState<CalendarDayDetailData | null>(null);
  const [progress, setProgress] = useState<CalendarProgressData | null>(null);
  const [activeTab, setActiveTab] = useState<"planning" | "progress">("planning");
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progressMenuVisible, setProgressMenuVisible] = useState(false);
  const [planMenuVisible, setPlanMenuVisible] = useState(false);
  const [progressMenuStage, setProgressMenuStage] = useState<"actions" | "date">("actions");
  const [progressStartDate, setProgressStartDate] = useState("");
  const [progressDateError, setProgressDateError] = useState<string | null>(null);
  const [progressDateBusy, setProgressDateBusy] = useState(false);

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
  useFocusEffect(useCallback(() => { if (status === "authenticated") void refreshProfile().catch(() => undefined); }, [refreshProfile, status]));
  useFocusEffect(useCallback(() => {
    if (status !== "authenticated" || !visibleMonth || extended) return;
    let active = true;
    setMonthError(null);
    void monthCache.load(visibleMonth)
      .then((data) => { if (active) { setMonthOverview({ key: visibleMonth, data }); monthCache.prefetchAdjacent(visibleMonth); } })
      .catch((nextError) => { if (active) setMonthError(userFacingError(nextError)); });
    return () => { active = false; };
  }, [extended, monthCache, status, visibleMonth]));
  useEffect(() => {
    if (!selectedDate || status !== "authenticated") return;
    let active = true;
    void apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${selectedDate}`)
      .then((next) => { if (active) setDetail(next); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
    return () => { active = false; };
  }, [apiRequest, selectedDate, status]);

  const week = useMemo(() => overview?.days.slice(0, 7) ?? [], [overview]);
  const monthDays = monthOverview?.key === visibleMonth ? monthOverview.data.days : [];
  const upcoming = useMemo(() => {
    if (!overview) return [];
    const future = overview.days.filter((day) => day.calendar_date >= overview.local_date);
    return extended ? future : future.slice(0, 7);
  }, [extended, overview]);
  const selectedDetail = detail?.calendar_date === selectedDate ? detail : null;
  const futurePlansCount = overview?.future_plans_count ?? 0;
  const calendarCoverage = progress && futurePlansCount ? Math.round(progress.days_with_plan / futurePlansCount * 100) : 0;
  const mealCoverage = progress?.scheduled_meals ? Math.round(progress.completed_meals / progress.scheduled_meals * 100) : 0;

  function changeVisibleMonth(delta: number) {
    if (!visibleMonth) return;
    const nextMonth = shiftMonth(visibleMonth, delta);
    const cached = monthCache.get(nextMonth);
    if (cached) setMonthOverview({ key: nextMonth, data: cached });
    setVisibleMonth(nextMonth);
  }
  async function adjustProgressStart() {
    setProgressDateBusy(true);
    setProgressDateError(null);
    try {
      const nextProgress = await apiRequest<CalendarProgressData>("/api/v1/calendar/progress/periods/current", {
        body: JSON.stringify({ start_date: progressStartDate }),
        method: "PUT",
      });
      setProgress(nextProgress);
      setProgressMenuVisible(false);
      setProgressMenuStage("actions");
    } catch (nextError) {
      setProgressDateError(userFacingError(nextError));
    } finally {
      setProgressDateBusy(false);
    }
  }
  function closeProgressMenu() {
    if (progressDateBusy) return;
    setProgressMenuVisible(false);
    setProgressMenuStage("actions");
    setProgressDateError(null);
  }
  function openProgressDatePicker() {
    setProgressStartDate(progress?.period_start ?? overview?.local_date ?? "");
    setProgressDateError(null);
    setProgressMenuStage("date");
  }
  function openDay(date: string) {
    router.push(`/calendar/days/${date}` as Href);
  }
  function openUpcomingDay(day: CalendarDay) {
    if (day.has_plan && day.id != null) {
      router.push(`/program/days/${day.id}` as Href);
    } else {
      openDay(day.calendar_date);
    }
  }
  function replaceUpcomingDay(day: CalendarDay) {
    router.push({ pathname: "/calendar/days/[date]", params: { date: day.calendar_date, section: "replace" } } as Href);
  }
  async function removeUpcomingDay(day: CalendarDay) {
    setError(null);
    try {
      await apiRequest(`/api/v1/calendar/days/${day.calendar_date}/plan`, { method: "DELETE" });
      await load();
    } catch (nextError) {
      setError(userFacingError(nextError));
      throw nextError;
    }
  }
  async function reorderUpcomingDays(dates: string[], orderedDayIds: (number | null)[]) {
    setError(null);
    try {
      await apiRequest("/api/v1/calendar/reorder", {
        body: JSON.stringify({ dates, ordered_day_ids: orderedDayIds }),
        method: "PUT",
      });
      await load();
    } catch (nextError) {
      setError(userFacingError(nextError));
      throw nextError;
    }
  }
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !overview) return <LoadingState label="Preparando tu calendario…" />;

  return (
    <>
    <Screen
      contentStyle={styles.content}
      headerMode={extended ? "preserve" : "automatic"}
      scrollHeader={!extended ? <SectionPageHeader countLabel="fechas" section="calendarization" subtitle="Trae tus planes y programas al calendario, y ejecútalos registrando su cumplimiento" title="Calendario" /> : undefined}
      stickyHeader={!extended ? <DistributedTabBar<"planning" | "progress">
        accessibilityLabel="Secciones del calendario"
        activeTab={activeTab}
        onChange={setActiveTab}
        tabs={[{ key: "planning", label: "Planificación" }, { key: "progress", label: "Progreso" }]}
      /> : undefined}
      stickyHeaderStyle={styles.stickyHeader}>
      {extended ? <SectionPageHeader countLabel="fechas" section="calendarization" subtitle="Fechas próximas, tengan o no un plan asignado." title="Planes próximas fechas" /> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {!extended && activeTab === "planning" ? (
        <>
          <View style={styles.calendarSection}>
            <View style={styles.monthNavigation}>
              <Pressable accessibilityLabel="Mes anterior" accessibilityRole="button" onPress={() => changeVisibleMonth(-1)} style={styles.monthArrow}>
                <ChevronLeft color={tokens.color.textMain} size={20} />
              </Pressable>
              <Text accessibilityRole="header" style={styles.monthTitle}>{visibleMonth ? monthLabel(visibleMonth) : ""}</Text>
              <Pressable accessibilityLabel="Mes siguiente" accessibilityRole="button" onPress={() => changeVisibleMonth(1)} style={styles.monthArrow}>
                <ChevronRight color={tokens.color.textMain} size={20} />
              </Pressable>
            </View>
            {visibleMonth && overview && visibleMonth !== monthKeyFromDate(overview.local_date) ? <Pressable accessibilityRole="button" onPress={() => setVisibleMonth(monthKeyFromDate(overview.local_date))}><Text style={styles.monthTodayLink}>Volver al mes actual</Text></Pressable> : null}
            {monthError ? <InlineNotice tone="error">{monthError}</InlineNotice> : null}
            {!monthDays.length && !monthError ? <CalendarMonthPlaceholder /> : <View style={styles.grid}>
              {(["L", "M", "M", "J", "V", "S", "D"] as const).map((label, index) => <Text key={`weekday-${index}`} style={styles.gridHeader}>{label}</Text>)}
              {monthDays.map((day) => (
                <Pressable
                  accessibilityLabel={`${dateLabel(day.calendar_date, { day: "numeric", month: "long", year: "numeric" })}: ${day.has_plan ? "Con plan" : "Sin plan"}${day.commitments?.length ? `; ${day.commitments.map((item) => commitmentPresentation[item.kind].label).join(", ")}` : ""}`}
                  accessibilityRole="button"
                  key={day.calendar_date}
                  onPress={() => openDay(day.calendar_date)}
                  style={[styles.gridDate, day.has_plan && styles.gridDateFilled, monthKeyFromDate(day.calendar_date) !== visibleMonth && styles.gridDateAdjacent, day.calendar_date === overview?.local_date && styles.gridDateToday]}>
                  <Text style={[styles.gridNumber, day.has_plan && styles.gridNumberWithPlan]}>{day.calendar_date.slice(8, 10)}</Text>
                  {day.commitments?.length ? <View style={styles.gridCommitmentDots}>{day.commitments.map((item) => <View key={item.id} style={[styles.gridCommitmentDot, { backgroundColor: commitmentPresentation[item.kind].color }]} />)}</View> : null}
                </Pressable>
              ))}
            </View>}
          </View>
          <View style={styles.summaryRow}>
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
          </View>
          <View style={styles.calendarizeActions}>
            <Button icon={<EntityIcon entity="dailyPlan" />} label="Calendarizar planes" onPress={() => setPlanMenuVisible(true)} variant="secondary" />
            <Button label="Ver registro de compromisos" onPress={() => router.push("/calendar/registry" as Href)} variant="secondary" />
          </View>
          <ProgramSectionHeader icon={CalendarDays} subtitle="Los próximos siete días, con o sin plan asignado." title="Planes próximas fechas" />
          <CalendarUpcomingPanels days={upcoming} onOpenDay={openUpcomingDay} onRemove={removeUpcomingDay} onReorder={reorderUpcomingDays} onReplace={replaceUpcomingDay} weightKg={profile?.current_weight_kg ?? null} />
          <Button label="Ver más fechas" onPress={() => router.push("/calendar/future" as Href)} variant="secondary" />

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
          {selectedDetail && !selectedDetail.has_execution ? <Button label={selectedDetail.has_plan ? "Cambiar plan de esta fecha" : "Asignar plan a esta fecha"} onPress={() => openDay(selectedDetail.calendar_date)} variant="secondary" /> : null}

        </>
      ) : null}

      {!extended && activeTab === "progress" && progress ? <>
        <View style={styles.progressHeaderSpacing}>
          <ProgramSectionHeader
            action={<Pressable accessibilityLabel="Opciones de progreso" accessibilityRole="button" onPress={() => setProgressMenuVisible(true)} style={styles.progressMenuButton}><Ellipsis color={tokens.color.textMain} size={24} /></Pressable>}
            detail={<Chip backgroundColor={tokens.color.surfaceMuted} borderColor={tokens.color.borderDefault} label={`Inicio el ${dateLabel(progress.period_start, { day: "numeric", month: "long" })}`} textColor={tokens.color.textMuted} />}
            icon={CalendarDays}
            title="Progreso"
          />
        </View>
        <ProgramActiveKpis
          adheredDays={progress.completed_meals}
          adherence={mealCoverage}
          bleed={false}
          elapsedDays={progress.days_with_plan}
          mealLabel="Comidas cumplidas"
          planLabel={"Planes\nrecorridos"}
          plannedAdherenceDays={progress.scheduled_meals}
          progress={calendarCoverage}
          standalone
          totalDays={futurePlansCount}
        />
      </> : null}

      {extended ? <CalendarUpcomingPanels days={upcoming} onOpenDay={openUpcomingDay} onRemove={removeUpcomingDay} onReorder={reorderUpcomingDays} onReplace={replaceUpcomingDay} weightKg={profile?.current_weight_kg ?? null} /> : null}
    </Screen>
    <ActionSheetModal onRequestClose={() => setPlanMenuVisible(false)} visible={planMenuVisible}>
      <SafeAreaView edges={["left", "right"]} style={styles.progressSheet}>
        <ActionSheetHeader icon={CalendarDays} onClose={() => setPlanMenuVisible(false)} title="Calendarizar planes" />
        <View style={styles.progressSheetContent}>
          <ActionSheetActions>
            <ActionSheetAction icon={ListPlus} label="Seleccionar planes individuales" onPress={() => { setPlanMenuVisible(false); router.push("/calendar/select-plans" as Href); }} />
            <ActionSheetAction icon={CalendarRange} label="Seleccionar programa semanal" onPress={() => { setPlanMenuVisible(false); router.push("/program/activate" as Href); }} />
          </ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
    <ActionSheetModal onRequestClose={closeProgressMenu} visible={progressMenuVisible}>
      <SafeAreaView edges={["left", "right"]} style={styles.progressSheet}>
        <ActionSheetHeader icon={CalendarDays} onClose={closeProgressMenu} title={progressMenuStage === "date" ? "Ajustar inicio del periodo" : "Progreso"} />
        <ScrollView contentContainerStyle={styles.progressSheetContent} showsVerticalScrollIndicator={false}>
          {progressDateError ? <InlineNotice tone="error">{progressDateError}</InlineNotice> : null}
          {progressMenuStage === "date" ? <>
            <Text style={styles.progressDateHelp}>Elige desde qué fecha quieres revisar tu progreso. Los registros anteriores permanecerán intactos.</Text>
            <NativeDateTimeField label="Fecha de inicio" maximumValue={overview?.local_date} mode="date" onChange={setProgressStartDate} value={progressStartDate} />
            <Button disabled={!progressStartDate || progressStartDate === progress?.period_start} label="Guardar fecha de inicio" loading={progressDateBusy} onPress={() => void adjustProgressStart()} />
            <Button label="Volver" onPress={() => setProgressMenuStage("actions")} variant="secondary" />
          </> : <>
            <ActionSheetActions>
              <ActionSheetAction icon={CalendarDays} label="Ajustar inicio periodo progreso" onPress={openProgressDatePicker} />
            </ActionSheetActions>
          </>}
        </ScrollView>
      </SafeAreaView>
    </ActionSheetModal>
    </>
  );
}

const styles = StyleSheet.create({
  calendarizeActions: { gap: tokens.spacing.sm },
  calendarSection: { marginBottom: 12, marginTop: -12, paddingVertical: tokens.spacing.sm },
  content: { gap: tokens.spacing.lg },
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: tokens.spacing.sm },
  gridDate: { alignItems: "center", borderColor: "transparent", borderRadius: 10, borderWidth: 2, justifyContent: "center", minHeight: 38, width: "13.5%" },
  gridDateAdjacent: { opacity: 0.5 },
  gridDateFilled: { backgroundColor: `${tokens.color.dailyPlan}33` },
  gridCommitmentDots: { bottom: 2, flexDirection: "row", gap: 2, position: "absolute" },
  gridCommitmentDot: { borderRadius: 3, height: 4, width: 4 },
  gridDateToday: { borderColor: tokens.color.success },
  gridHeader: { color: tokens.color.textMuted, fontSize: 11, textAlign: "center", width: "13.5%" },
  gridNumber: { color: tokens.color.textMain, fontSize: 14, fontWeight: "500" },
  gridNumberWithPlan: { color: tokens.color.textMain, fontWeight: "700" },
  gridPlaceholderDate: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: 10, justifyContent: "center", minHeight: 38, opacity: 0.55, width: "13.5%" },
  gridPlaceholderNumber: { backgroundColor: tokens.color.borderStrong, borderRadius: tokens.radius.pill, height: 5, opacity: 0.7, width: 14 },
  monthArrow: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: 10, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  monthNavigation: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: tokens.spacing.md },
  monthTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: "600" },
  monthTodayLink: { color: tokens.color.interactivePrimary, fontSize: 13, marginBottom: tokens.spacing.sm, textAlign: "center" },
  progressMenuButton: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: 18, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  progressHeaderSpacing: { marginTop: 0 },
  progressDateHelp: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  progressSheet: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  progressSheetContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  summaryCard: { backgroundColor: tokens.color.surfaceCard, borderRadius: tokens.radius.panel, flex: 1, gap: tokens.spacing.xs, justifyContent: "space-between", minHeight: 122, padding: tokens.spacing.md },
  summaryDateValue: { color: tokens.color.textMain, fontSize: 20, fontWeight: "700" },
  summaryHint: { color: tokens.color.textMuted, fontSize: 12 },
  summaryLabel: { color: tokens.color.textMain, fontSize: 14, fontWeight: "600" },
  summaryRow: { flexDirection: "row", gap: tokens.spacing.sm },
  summaryValue: { color: tokens.color.textMain, fontSize: 32, fontWeight: "700", fontVariant: ["tabular-nums"] },
  stickyHeader: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, paddingTop: tokens.spacing.sm },
  pressed: { opacity: 0.65 },
});
