import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { Bell, CalendarCheck2, CalendarClock, CalendarDays, ClipboardList, Ellipsis, Plus, Weight } from "lucide-react-native";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarDay, CalendarOverviewData, CalendarProgressData, WeightItem, WeightListData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarDaySectionHeading } from "@/components/calendarization/calendar-day-section-heading";
import { CalendarizeActions } from "@/components/calendarization/calendarize-actions";
import { CalendarUpcomingPanels } from "@/components/calendarization/calendar-upcoming-panels";
import { CalendarMonthCalendar } from "@/components/calendarization/calendar-month-calendar";
import { commitmentActionLabel, commitmentKinds, commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { CalendarWeekMetrics } from "@/components/calendarization/calendar-week-metrics";
import { monthKeyFromDate, shiftMonth } from "@/components/calendarization/calendar-month";
import { commitmentsForUpcomingDays, type CommitmentScope } from "@/components/calendarization/calendar-commitment-registry";
import { CalendarCommitmentListCard } from "@/components/calendarization/calendar-commitment-list-card";
import { createCalendarMonthCache } from "@/components/calendarization/calendar-month-cache";
import { calendarWeekRangeLabel, groupCalendarDaysByIsoWeek } from "@/components/calendarization/calendar-weeks";
import { PickerCardAction } from "@/components/pickers/picker-card-action";
import { ProgramSectionHeader } from "@/components/programs/program-section-header";
import { ProgramActiveKpis } from "@/components/programs/program-active-kpis";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, Card, Chip, DistributedTabBar, EntityIcon, InlineNotice, LoadingState, NativeDateTimeField, Screen, ScrollableTabBar, SectionPageHeader, WeightTrendCard } from "@/components/ui";
import { tokens } from "@/design/tokens";

function dateLabel(value: string, options: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat("es-CL", options).format(new Date(`${value}T12:00:00`));
}

const commitmentTabLabels = { shopping: "Hacer compras", cooking: "Cocinar", training: "Entrenar", nutritionist: "Evaluación" } as const;
const commitmentMetricLabels = { shopping: "Compras", cooking: "Cocinar", training: "Entrenar", nutritionist: "Evaluación" } as const;

export function CalendarOverviewScreen({ extended = false }: { extended?: boolean }) {
  const router = useRouter();
  const setHeaderPresentation = useHeaderPresentation();
  const { apiRequest, profile, refreshProfile, status } = useSession();
  const monthCache = useMemo(() => createCalendarMonthCache(apiRequest), [apiRequest]);
  const [overview, setOverview] = useState<CalendarOverviewData | null>(null);
  const [visibleMonth, setVisibleMonth] = useState<string | null>(null);
  const [monthOverview, setMonthOverview] = useState<{ key: string; data: CalendarOverviewData } | null>(null);
  const [monthError, setMonthError] = useState<string | null>(null);
  const [progress, setProgress] = useState<CalendarProgressData | null>(null);
  const [weightItems, setWeightItems] = useState<WeightItem[]>([]);
  const [activeTab, setActiveTab] = useState<"planning" | "progress">("planning");
  const [commitmentScope, setCommitmentScope] = useState<CommitmentScope>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progressMenuVisible, setProgressMenuVisible] = useState(false);
  const [calendarMenuVisible, setCalendarMenuVisible] = useState(false);
  const [calendarOptionsVisible, setCalendarOptionsVisible] = useState(false);
  const [commitmentMenuVisible, setCommitmentMenuVisible] = useState(false);
  const [planMenuVisible, setPlanMenuVisible] = useState(false);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [progressMenuStage, setProgressMenuStage] = useState<"actions" | "date">("actions");
  const [progressStartDate, setProgressStartDate] = useState("");
  const [progressDateError, setProgressDateError] = useState<string | null>(null);
  const [progressDateBusy, setProgressDateBusy] = useState(false);
  const loadSequence = useRef(0);

  useFocusEffect(useCallback(() => {
    if (extended) {
      setHeaderPresentation({ action: { icon: "plus", label: "Calendarizar minuta o programa", onPress: () => setPlanMenuVisible(true) }, fallback: "/calendar", identityVisible: compactHeaderVisible, mode: "back", title: "Próximas minutas programadas" });
    } else {
      setHeaderPresentation({ action: { icon: "more", label: "Opciones de Mi calendario", onPress: () => setCalendarOptionsVisible(true) }, createAction: { icon: "plus", label: "Calendarizar", onPress: () => setCalendarMenuVisible(true) }, identityVisible: compactHeaderVisible, mode: "default", title: "Mi calendario" });
    }
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, extended, setHeaderPresentation]));

  const load = useCallback(async () => {
    const sequence = ++loadSequence.current;
    setLoading(true);
    setError(null);
    try {
      const progressRequest = (extended ? Promise.resolve(null) : apiRequest<CalendarProgressData>("/api/v1/calendar/progress"))
        .catch((nextError) => {
          if (sequence === loadSequence.current) setError(userFacingError(nextError));
          return null;
        });
      const weightRequest = extended
        ? Promise.resolve(null)
        : apiRequest<WeightListData>("/api/v1/weights?limit=12").catch(() => null);
      const nextOverview = await apiRequest<CalendarOverviewData>(`/api/v1/calendar?days=${extended ? 42 : 35}`);
      if (sequence !== loadSequence.current) return;
      setOverview(nextOverview);
      setVisibleMonth((previous) => previous ?? monthKeyFromDate(nextOverview.local_date));
      setLoading(false);
      const [nextProgress, weightHistory] = await Promise.all([progressRequest, weightRequest]);
      if (sequence !== loadSequence.current) return;
      setProgress(nextProgress);
      setWeightItems(weightHistory?.items ?? []);
    } catch (nextError) {
      if (sequence === loadSequence.current) setError(userFacingError(nextError));
    } finally {
      if (sequence === loadSequence.current) setLoading(false);
    }
  }, [apiRequest, extended]);

  useEffect(() => () => { loadSequence.current += 1; }, []);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => { if (status === "authenticated" && !extended) void refreshProfile().catch(() => undefined); }, [extended, refreshProfile, status]));
  useFocusEffect(useCallback(() => {
    if (status !== "authenticated" || !visibleMonth || extended) return;
    let active = true;
    setMonthError(null);
    void monthCache.load(visibleMonth)
      .then((data) => { if (active) setMonthOverview({ key: visibleMonth, data }); })
      .catch((nextError) => { if (active) setMonthError(userFacingError(nextError)); });
    return () => { active = false; };
  }, [extended, monthCache, status, visibleMonth]));
  const todayDay = useMemo(() => overview?.days.find((day) => day.calendar_date === overview.local_date) ?? null, [overview]);
  const hasTodayPlanChips = Boolean(todayDay?.has_plan || todayDay?.commitments?.length);
  const monthDays = useMemo(() => monthOverview?.key === visibleMonth ? monthOverview.data.days : [], [monthOverview, visibleMonth]);
  const visibleCommitments = useMemo(() => overview
    ? commitmentsForUpcomingDays(overview.days, overview.local_date, 7, commitmentScope) : [],
  [commitmentScope, overview]);
  const upcoming = useMemo(() => {
    if (!overview) return [];
    const future = overview.days.filter((day) => day.calendar_date >= overview.local_date);
    return extended ? future : future.slice(0, 7);
  }, [extended, overview]);
  const upcomingWeeks = useMemo(() => extended && overview
    ? groupCalendarDaysByIsoWeek(overview.days).filter((week) => week.days.at(-1)!.calendar_date >= overview.local_date)
    : groupCalendarDaysByIsoWeek(upcoming), [extended, overview, upcoming]);
  const futurePlansCount = overview?.future_plans_count ?? 0;
  const visibleFutureCommitmentCounts = useMemo(() => {
    const counts = { shopping: 0, cooking: 0, training: 0, nutritionist: 0 };
    if (!overview) return counts;
    overview.days.forEach((day) => {
      if (day.calendar_date < overview.local_date) return;
      day.commitments?.forEach((commitment) => { counts[commitment.kind] += 1; });
    });
    return counts;
  }, [overview]);
  const futureCommitmentCounts = overview?.future_commitments_count_by_kind ?? visibleFutureCommitmentCounts;
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
  function assignUpcomingDay(day: CalendarDay) {
    router.push({ pathname: "/calendar/days/[date]", params: { date: day.calendar_date, section: "assign" } } as Href);
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
  if (loading && !overview) return <LoadingState label={extended ? "Preparando tus próximas minutas…" : "Preparando tu calendario…"} />;

  return (
    <>
    <Screen
      contentStyle={styles.content}
      headerMode="preserve"
      onHeaderVisibilityChange={setCompactHeaderVisible}
      scrollHeader={!extended ? <SectionPageHeader countLabel="fechas" section="calendarization" subtitle="Planifica tus minutas, programas y compromisos en el calendario" title="Mi calendario" /> : undefined}
      stickyHeader={!extended ? <DistributedTabBar<"planning" | "progress">
        accessibilityLabel="Secciones del calendario"
        activeTab={activeTab}
        onChange={setActiveTab}
        tabs={[{ key: "planning", label: "Planificación" }, { key: "progress", label: "Progreso" }]}
      /> : undefined}
      stickyHeaderStyle={styles.stickyHeader}>
      {extended ? <SectionPageHeader countLabel="fechas" icon={<ClipboardList color={tokens.color.textMain} size={28} strokeWidth={1.8} />} section="calendarization" subtitle="Fechas próximas, tengan o no un plan asignado." title="Próximas minutas programadas" /> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {!extended && activeTab === "planning" ? (
        <>
          <View style={styles.calendarBlock}>
            {overview ? <View style={[styles.todayHeadingSpacing, hasTodayPlanChips && styles.todayHeadingWithChips]}><CalendarDaySectionHeading commitments={todayDay?.commitments} date={overview.local_date} hasPlan={todayDay?.has_plan} today={overview.local_date} /></View> : null}
            {visibleMonth && overview ? <View style={styles.calendarMonthSpacing}><CalendarMonthCalendar days={monthDays} embedded error={monthError} localDate={overview.local_date} onChangeMonth={changeVisibleMonth} onOpenDay={openDay} onReturnToCurrentMonth={() => setVisibleMonth(monthKeyFromDate(overview.local_date))} visibleMonth={visibleMonth} /></View> : null}
            <View style={styles.upcomingCommitmentsSection}>
              <View style={styles.upcomingCommitmentsHeading}>
                <CalendarCheck2 color={tokens.color.textMain} size={16} strokeWidth={2.1} />
                <Text accessibilityRole="header" style={styles.upcomingCommitmentsTitle}>Minutas y compromisos programados</Text>
              </View>
              <View style={styles.upcomingCommitmentsDashboard}>
                <Pressable accessibilityLabel={`Ver próximas minutas programadas: ${futurePlansCount} ${futurePlansCount === 1 ? "minuta" : "minutas"}`} accessibilityRole="button" onPress={() => router.push("/calendar/future" as Href)} style={({ pressed }) => [styles.upcomingCommitmentsMetric, { backgroundColor: `${tokens.color.dailyPlan}33` }, pressed && styles.pressed]}>
                  <View style={styles.upcomingCommitmentsMetricValueRow}>
                    <View style={[styles.upcomingCommitmentsIcon, { backgroundColor: tokens.color.dailyPlan }]}><ClipboardList color={tokens.color.entityIconForeground} size={14} strokeWidth={2.1} /></View>
                    <Text style={styles.upcomingCommitmentsValue}>{futurePlansCount}</Text>
                  </View>
                  <Text numberOfLines={2} style={styles.upcomingCommitmentsMetricLabel}>Minutas</Text>
                </Pressable>
                {commitmentKinds.map((kind) => {
                  const presentation = commitmentPresentation[kind];
                  const Icon = presentation.icon;
                  return <Pressable accessibilityLabel={`Ver compromisos de ${commitmentMetricLabels[kind]}: ${futureCommitmentCounts[kind]}`} accessibilityRole="button" key={kind} onPress={() => router.push({ pathname: "/calendar/future-commitments", params: { kind } })} style={({ pressed }) => [styles.upcomingCommitmentsMetric, { backgroundColor: `${presentation.color}33` }, pressed && styles.pressed]}>
                    <View style={styles.upcomingCommitmentsMetricValueRow}>
                      <View style={[styles.upcomingCommitmentsIcon, { backgroundColor: `${presentation.color}33` }]}><Icon color={presentation.color} size={14} strokeWidth={2.1} /></View>
                      <Text style={styles.upcomingCommitmentsValue}>{futureCommitmentCounts[kind]}</Text>
                    </View>
                    <Text numberOfLines={2} style={styles.upcomingCommitmentsMetricLabel}>{commitmentMetricLabels[kind]}</Text>
                  </Pressable>;
                })}
              </View>
            </View>
            <View style={styles.calendarAddActions}>
              <View style={styles.calendarAddAction}><PickerCardAction icon={<Plus color={tokens.color.textMain} size={17} strokeWidth={2.1} />} label="Añadir minuta" onPress={() => setPlanMenuVisible(true)} subject="Mi calendario" variant="cardFullWidth" /></View>
              <View style={styles.calendarAddAction}><PickerCardAction icon={<Plus color={tokens.color.textMain} size={17} strokeWidth={2.1} />} label="Añadir compromiso" onPress={() => setCommitmentMenuVisible(true)} subject="Mi calendario" variant="cardFullWidth" /></View>
            </View>
          </View>
          <ProgramSectionHeader icon={ClipboardList} subtitle="Los próximos siete días, con o sin plan asignado." title="Mis minutas programadas" />
          <View style={styles.minutePanels}>
            <View style={styles.upcomingMetricsSpacing}>
              <CalendarWeekMetrics days={upcoming} weightKg={profile?.current_weight_kg ?? null} />
            </View>
            <CalendarUpcomingPanels days={upcoming} localDate={overview?.local_date ?? ""} onAssign={assignUpcomingDay} onOpenDay={openUpcomingDay} onRemove={removeUpcomingDay} onReorder={reorderUpcomingDays} onReplace={replaceUpcomingDay} weightKg={profile?.current_weight_kg ?? null} />
          </View>
          <Button label="Ver más fechas" onPress={() => router.push("/calendar/future" as Href)} variant="secondary" />

          <ProgramSectionHeader bottomSpacing={0} icon={CalendarCheck2} subtitle="Tus compromisos en los próximos siete días." title="Mis compromisos programados" />
          <View style={styles.commitmentFilters}>
            <ScrollableTabBar<CommitmentScope>
              accessibilityLabel="Tipos de compromisos"
              activeTab={commitmentScope}
              density="compact"
              onChange={setCommitmentScope}
              tabs={[{ key: "all", label: "Todos" }, ...commitmentKinds.map((kind) => {
                const presentation = commitmentPresentation[kind];
                const Icon = presentation.icon;
                return { icon: (selected: boolean) => <Icon color={selected ? tokens.color.surfaceApp : presentation.color} size={14} strokeWidth={2.1} />, key: kind, label: commitmentTabLabels[kind] };
              })]}
            />
          </View>
          <View style={styles.commitmentsListHeading}>
            <Text accessibilityRole="header" style={styles.commitmentsListTitle}>Próximos 7 días</Text>
          </View>
          {!overview ? <LoadingState label="Cargando compromisos…" mode="content" /> : null}
          {overview && !visibleCommitments.length ? <Card><Text style={styles.commitmentsEmpty}>No hay compromisos programados para los próximos siete días.</Text></Card> : null}
          {visibleCommitments.map((commitment) => <CalendarCommitmentListCard
            commitment={commitment}
            key={commitment.id}
            onCreateFoodList={() => router.push(`/calendar/commitments/${commitment.id}/foods?date=${commitment.calendar_date}` as Href)}
            onPress={() => router.push(`/calendar/commitments/${commitment.id}?date=${commitment.calendar_date}` as Href)}
            showFoodListDetails
          />)}
          <Button label="Ver más fechas" onPress={() => router.push("/calendar/future-commitments" as Href)} variant="secondary" />

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
        <WeightTrendCard items={weightItems} />
        <Button icon={<Weight color={tokens.color.textMain} size={20} strokeWidth={2} />} label="Registrar peso" onPress={() => router.push("/weight" as Href)} variant="secondary" />
      </> : null}

      {extended ? upcomingWeeks.map((calendarWeek, index) => <View key={calendarWeek.key} style={[styles.futureWeekSection, index > 0 && styles.futureWeekSpacing]}>
        <ProgramSectionHeader
          icon={CalendarDays}
          subtitle={calendarWeekRangeLabel(calendarWeek.days)}
          subtitleTopSpacing={-4}
          title={`Semana ${calendarWeek.weekNumber}`}
        />
        <View style={styles.futureWeekPanels}>
          <View style={styles.futureWeekMetrics}>
              <CalendarWeekMetrics days={calendarWeek.days} expandedLayout localDate={overview?.local_date} weightKg={profile?.current_weight_kg ?? null} />
          </View>
          <CalendarUpcomingPanels days={calendarWeek.days} expandedLayout localDate={overview?.local_date ?? ""} onAssign={assignUpcomingDay} onOpenDay={openUpcomingDay} onRemove={removeUpcomingDay} onReorder={reorderUpcomingDays} onReplace={replaceUpcomingDay} weightKg={profile?.current_weight_kg ?? null} />
        </View>
      </View>) : null}
    </Screen>
    <CalendarizeActions onClose={() => setCalendarMenuVisible(false)} visible={calendarMenuVisible} />
    <ActionSheetModal onRequestClose={() => setCalendarOptionsVisible(false)} visible={calendarOptionsVisible}>
      <SafeAreaView edges={["left", "right"]} style={styles.progressSheet}>
        <ActionSheetHeader icon={Ellipsis} onClose={() => setCalendarOptionsVisible(false)} title="Opciones de Mi calendario" />
        <View style={styles.progressSheetContent}>
          <ActionSheetActions>
            <ActionSheetAction icon={Bell} label="Configurar notificaciones de compromisos" onPress={() => { setCalendarOptionsVisible(false); router.push("/calendar/commitment-notifications" as Href); }} />
          </ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
    <ActionSheetModal onRequestClose={() => setCommitmentMenuVisible(false)} visible={commitmentMenuVisible}>
      <SafeAreaView edges={["left", "right"]} style={styles.progressSheet}>
        <ActionSheetHeader icon={CalendarCheck2} onClose={() => setCommitmentMenuVisible(false)} title="Registrar compromiso" />
        <View style={styles.progressSheetContent}>
          <ActionSheetActions>
            {commitmentKinds.map((kind) => <ActionSheetAction
              icon={commitmentPresentation[kind].icon}
              iconBackgroundColor={`${commitmentPresentation[kind].color}33`}
              iconColor={commitmentPresentation[kind].color}
              key={kind}
              label={commitmentActionLabel[kind]}
              onPress={() => {
                setCommitmentMenuVisible(false);
                router.push(`/calendar/commitments?kind=${kind}` as Href);
              }}
            />)}
          </ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
    <ActionSheetModal onRequestClose={() => setPlanMenuVisible(false)} visible={planMenuVisible}>
      <SafeAreaView edges={["left", "right"]} style={styles.progressSheet}>
        <ActionSheetHeader icon={CalendarClock} onClose={() => setPlanMenuVisible(false)} title="Calendarizar planes" />
        <View style={styles.progressSheetContent}>
          <ActionSheetActions>
            <ActionSheetAction iconNode={<EntityIcon entity="dailyPlan" size="compact" />} label="Calendarizar minuta" onPress={() => { setPlanMenuVisible(false); router.push("/calendar/select-plans" as Href); }} />
            <ActionSheetAction iconNode={<EntityIcon entity="program" size="compact" />} label="Calendarizar programa" onPress={() => { setPlanMenuVisible(false); router.push("/program/activate" as Href); }} />
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
  calendarAddAction: { flex: 1, minWidth: 0 },
  calendarAddActions: { flexDirection: "row", gap: tokens.spacing.sm, marginHorizontal: -6 },
  calendarBlock: { gap: tokens.spacing.sm, marginTop: -6 },
  calendarMonthSpacing: { marginBottom: 10 },
  commitmentsEmpty: { color: tokens.color.textMuted, fontSize: 13 },
  commitmentFilters: { marginTop: -4 },
  commitmentsListHeading: { gap: tokens.spacing.sm },
  commitmentsListTitle: { color: tokens.color.textMain, fontSize: 16, fontWeight: tokens.weight.bold },
  content: { gap: tokens.spacing.lg },
  futureWeekMetrics: { marginTop: tokens.spacing.md - 18 },
  futureWeekPanels: { gap: tokens.spacing.md },
  futureWeekSection: { gap: 0 },
  futureWeekSpacing: { marginTop: 18 },
  progressMenuButton: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: 18, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  progressHeaderSpacing: { marginTop: -42 },
  progressDateHelp: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  progressSheet: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  progressSheetContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  minutePanels: { gap: tokens.spacing.md },
  upcomingMetricsSpacing: { marginTop: -20 },
  stickyHeader: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, paddingTop: tokens.spacing.sm },
  todayHeadingSpacing: { marginBottom: 12 },
  todayHeadingWithChips: { marginBottom: 4 },
  upcomingCommitmentsDashboard: { flexDirection: "row", gap: tokens.spacing.xs, marginBottom: 4, marginHorizontal: -6 },
  upcomingCommitmentsHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  upcomingCommitmentsIcon: { alignItems: "center", borderRadius: 8, height: 24, justifyContent: "center", width: 24 },
  upcomingCommitmentsMetric: { alignItems: "center", borderRadius: tokens.radius.md, flex: 1, gap: 3, minWidth: 0, paddingHorizontal: 3, paddingVertical: tokens.spacing.sm + 4 },
  upcomingCommitmentsMetricLabel: { color: tokens.color.textMain, flexShrink: 1, fontSize: 10, lineHeight: 12, textAlign: "center", width: "100%" },
  upcomingCommitmentsMetricValueRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  upcomingCommitmentsSection: { gap: tokens.spacing.md, marginTop: 12 },
  upcomingCommitmentsTitle: { color: tokens.color.textMain, fontSize: 15, fontWeight: tokens.weight.semibold },
  upcomingCommitmentsValue: { color: tokens.color.textMain, fontSize: 18, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold },
  pressed: { opacity: 0.65 },
});
