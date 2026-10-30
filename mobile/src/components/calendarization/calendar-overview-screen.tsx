import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { CalendarClock, CalendarDays, ChartNoAxesCombined, ChevronRight, ClipboardList, Clock, Ellipsis, Pin, Plus, Weight } from "lucide-react-native";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarDay, CalendarDayDetailData, CalendarOverviewData, CalendarProgressData, WeightItem, WeightListData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarizedDailyPlanCard } from "@/components/calendarization/calendarized-daily-plan-card";
import { CalendarDaySectionHeading } from "@/components/calendarization/calendar-day-section-heading";
import { CalendarizeActions } from "@/components/calendarization/calendarize-actions";
import { CalendarUpcomingPanels } from "@/components/calendarization/calendar-upcoming-panels";
import { CalendarMonthCalendar } from "@/components/calendarization/calendar-month-calendar";
import { commitmentActionLabel, commitmentKinds, commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { CalendarWeekMetrics } from "@/components/calendarization/calendar-week-metrics";
import { monthKeyFromDate, shiftMonth } from "@/components/calendarization/calendar-month";
import { createCalendarMonthCache } from "@/components/calendarization/calendar-month-cache";
import { calendarWeekRangeLabel, groupCalendarDaysByIsoWeek } from "@/components/calendarization/calendar-weeks";
import { ProgramDaySelector } from "@/components/libraries/program-planning-controls";
import { pickerHref } from "@/components/pickers/picker-routes";
import { PickerCardAction } from "@/components/pickers/picker-card-action";
import { ProgramSectionHeader } from "@/components/programs/program-section-header";
import { ProgramActiveKpis } from "@/components/programs/program-active-kpis";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, Card, Chip, DistributedTabBar, EntityIcon, InlineNotice, LoadingState, NativeDateTimeField, Screen, SectionPageHeader, WeightTrendCard } from "@/components/ui";
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

export function CalendarOverviewScreen({ extended = false }: { extended?: boolean }) {
  const router = useRouter();
  const setHeaderPresentation = useHeaderPresentation();
  const { apiRequest, profile, refreshProfile, status } = useSession();
  const monthCache = useMemo(() => createCalendarMonthCache(apiRequest), [apiRequest]);
  const [overview, setOverview] = useState<CalendarOverviewData | null>(null);
  const [visibleMonth, setVisibleMonth] = useState<string | null>(null);
  const [monthOverview, setMonthOverview] = useState<{ key: string; data: CalendarOverviewData } | null>(null);
  const [monthError, setMonthError] = useState<string | null>(null);
  const [detail, setDetail] = useState<CalendarDayDetailData | null>(null);
  const [progress, setProgress] = useState<CalendarProgressData | null>(null);
  const [weightItems, setWeightItems] = useState<WeightItem[]>([]);
  const [activeTab, setActiveTab] = useState<"planning" | "progress">("planning");
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [calendarSelectedDate, setCalendarSelectedDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progressMenuVisible, setProgressMenuVisible] = useState(false);
  const [calendarMenuVisible, setCalendarMenuVisible] = useState(false);
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
      setHeaderPresentation({ fallback: "/calendar", identityVisible: compactHeaderVisible, mode: "back", title: "Próximas minutas programadas" });
    } else {
      setHeaderPresentation({ createAction: { icon: "plus", label: "Calendarizar", onPress: () => setCalendarMenuVisible(true) }, identityVisible: compactHeaderVisible, mode: "default", title: "Mi calendario" });
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
      setSelectedDate((previous) => previous && nextOverview.days.some((day) => day.calendar_date === previous)
        ? previous : nextOverview.local_date);
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
  useEffect(() => {
    if (extended || !selectedDate || status !== "authenticated") return;
    let active = true;
    void apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${selectedDate}`)
      .then((next) => { if (active) setDetail(next); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
    return () => { active = false; };
  }, [apiRequest, extended, selectedDate, status]);

  const week = useMemo(() => overview?.days.slice(0, 7) ?? [], [overview]);
  const monthDays = useMemo(() => monthOverview?.key === visibleMonth ? monthOverview.data.days : [], [monthOverview, visibleMonth]);
  const selectedCalendarDate = calendarSelectedDate ?? overview?.local_date;
  const selectedCalendarDay = monthDays.find((day) => day.calendar_date === selectedCalendarDate)
    ?? overview?.days.find((day) => day.calendar_date === selectedCalendarDate);
  const selectedCommitments = selectedCalendarDay?.commitments ?? [];
  const assignedCommitments = useMemo(() => monthDays
    .filter((day) => monthKeyFromDate(day.calendar_date) === visibleMonth)
    .flatMap((day) => day.commitments ?? []), [monthDays, visibleMonth]);
  const assignedCommitmentsCount = assignedCommitments.length;
  const nextAssignedCommitment = assignedCommitments.find((commitment) => commitment.calendar_date >= (overview?.local_date ?? "")) ?? null;
  const lastAssignedCommitmentDate = assignedCommitments.length ? assignedCommitments[assignedCommitments.length - 1].calendar_date : null;
  const firstColumnCount = Math.ceil(selectedCommitments.length / 2);
  const upcoming = useMemo(() => {
    if (!overview) return [];
    const future = overview.days.filter((day) => day.calendar_date >= overview.local_date);
    return extended ? future : future.slice(0, 7);
  }, [extended, overview]);
  const upcomingWeeks = useMemo(() => groupCalendarDaysByIsoWeek(upcoming), [upcoming]);
  const fullCalendarWeeks = useMemo(() => new Map(groupCalendarDaysByIsoWeek(overview?.days ?? []).map((week) => [week.key, week.days])), [overview]);
  const selectedDetail = detail?.calendar_date === selectedDate ? detail : null;
  const selectedDayId = selectedDetail?.id;
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
  const nextScheduledPlan = useMemo(() => overview?.days.find((day) => day.calendar_date >= overview.local_date && day.has_plan) ?? null, [overview]);
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
      {extended ? <SectionPageHeader countLabel="fechas" section="calendarization" subtitle="Fechas próximas, tengan o no un plan asignado." title="Próximas minutas programadas" /> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {!extended && activeTab === "planning" ? (
        <>
          <View style={styles.upcomingCommitmentsSection}>
            <View style={styles.upcomingCommitmentsHeading}>
              <Clock color={tokens.color.textMain} size={16} strokeWidth={2.1} />
              <Text accessibilityRole="header" style={styles.upcomingCommitmentsTitle}>Próximos compromisos</Text>
            </View>
            <View accessibilityLabel="Minutas y próximos compromisos programados" accessible style={styles.upcomingCommitmentsDashboard}>
              <View accessibilityLabel={`${futurePlansCount} minutas programadas`} style={[styles.upcomingCommitmentsMetric, { backgroundColor: `${tokens.color.dailyPlan}33` }]}>
                <View style={styles.upcomingCommitmentsMetricValueRow}>
                  <View style={[styles.upcomingCommitmentsIcon, { backgroundColor: `${tokens.color.dailyPlan}33` }]}><ClipboardList color={tokens.color.dailyPlan} size={14} strokeWidth={2.1} /></View>
                  <Text style={styles.upcomingCommitmentsValue}>{futurePlansCount}</Text>
                </View>
              </View>
              {commitmentKinds.map((kind) => {
                const presentation = commitmentPresentation[kind];
                const Icon = presentation.icon;
                return <View accessibilityLabel={`${futureCommitmentCounts[kind]} ${commitmentActionLabel[kind]}`} key={kind} style={[styles.upcomingCommitmentsMetric, { backgroundColor: `${presentation.color}33` }]}>
                  <View style={styles.upcomingCommitmentsMetricValueRow}>
                    <View style={[styles.upcomingCommitmentsIcon, { backgroundColor: `${presentation.color}33` }]}><Icon color={presentation.color} size={14} strokeWidth={2.1} /></View>
                    <Text style={styles.upcomingCommitmentsValue}>{futureCommitmentCounts[kind]}</Text>
                  </View>
                </View>;
              })}
            </View>
          </View>
          <View style={styles.calendarBlock}>
            {visibleMonth && overview ? <CalendarMonthCalendar days={monthDays} error={monthError} localDate={overview.local_date} onChangeMonth={changeVisibleMonth} onOpenDay={setCalendarSelectedDate} onReturnToCurrentMonth={() => setVisibleMonth(monthKeyFromDate(overview.local_date))} selectedDate={selectedCalendarDate} visibleMonth={visibleMonth} /> : null}
            <View style={styles.calendarAddActions}>
              <View style={styles.calendarAddAction}><PickerCardAction icon={<Plus color={tokens.color.textMain} size={17} strokeWidth={2.1} />} label="Añadir minuta" onPress={() => setPlanMenuVisible(true)} subject="Mi calendario" variant="cardFullWidth" /></View>
              <View style={styles.calendarAddAction}><PickerCardAction icon={<Plus color={tokens.color.textMain} size={17} strokeWidth={2.1} />} label="Añadir compromiso" onPress={() => setCommitmentMenuVisible(true)} subject="Mi calendario" variant="cardFullWidth" /></View>
            </View>
          </View>
          <View style={styles.todaySection}>
            {selectedCalendarDate && overview?.local_date ? <CalendarDaySectionHeading date={selectedCalendarDate} today={overview.local_date} /> : null}
            <Card style={styles.todayCard}>
              {selectedCalendarDay?.has_plan ? <Pressable accessibilityRole="button" onPress={() => selectedCalendarDay.id != null ? router.push(`/program/days/${selectedCalendarDay.id}` as Href) : openDay(selectedCalendarDay.calendar_date)} style={styles.todayRow}>
                <EntityIcon cornerRadius={8} entity="dailyPlan" />
                <Text numberOfLines={1} style={styles.todayRowTitle}>{selectedCalendarDay.plan_name}</Text>
              </Pressable> : null}
              {selectedCommitments.length ? <View style={styles.todayCommitmentColumns}>
                {[selectedCommitments.slice(0, firstColumnCount), selectedCommitments.slice(firstColumnCount)].map((column, index) => <View key={index} style={styles.todayCommitmentColumn}>
                  {column.map((commitment) => {
                    const presentation = commitmentPresentation[commitment.kind];
                    const Icon = presentation.icon;
                    return <Pressable accessibilityRole="button" key={commitment.id} onPress={() => router.push(`/calendar/commitments/${commitment.id}?date=${commitment.calendar_date}` as Href)} style={styles.todayRow}>
                      <View style={[styles.todayCommitmentIcon, { backgroundColor: `${presentation.color}33` }]}><Icon color={presentation.color} size={16} strokeWidth={2.1} /></View>
                      <Text numberOfLines={1} style={styles.todayRowTitle}>{presentation.label}</Text>
                    </Pressable>;
                  })}
                </View>)}
              </View> : null}
              {!selectedCalendarDay?.has_plan && !selectedCalendarDay?.commitments?.length ? <Text style={styles.todayEmpty}>No hay minuta ni compromisos para esta fecha.</Text> : null}
              {selectedCalendarDate ? <View style={styles.todayDetailButton}><PickerCardAction label="Ver detalle del día" onPress={() => openDay(selectedCalendarDate)} subject={dateLabel(selectedCalendarDate, { day: "numeric", month: "long", year: "numeric" })} variant="mutedFullWidth" /></View> : null}
            </Card>
          </View>
          <ProgramSectionHeader icon={CalendarClock} title="Resumen minutas y compromisos" />
          <View style={styles.calendarizeActions}>
            <Card style={styles.commitmentsCard}>
              <View style={styles.commitmentsCardOverview}>
                <View style={styles.commitmentsCardCopy}>
                  <View style={styles.commitmentsCardHeading}>
                    <CalendarClock color={tokens.color.textMain} size={18} strokeWidth={2.1} />
                    <Text accessibilityRole="header" style={styles.commitmentsCardTitle}>Minutas programadas</Text>
                  </View>
                </View>
                <View accessibilityLabel="Minutas y programas" accessible style={styles.commitmentsCardIcons}>
                  <View style={[styles.commitmentsCardIcon, { backgroundColor: tokens.color.dailyPlan }]}><ClipboardList color={tokens.color.entityIconForeground} size={14} strokeWidth={2.1} /></View>
                  <View style={[styles.commitmentsCardIcon, { backgroundColor: tokens.color.program }]}><ChartNoAxesCombined color={tokens.color.entityIconForeground} size={14} strokeWidth={2.1} /></View>
                </View>
              </View>
              <View style={styles.planningSummary}>
                <View style={styles.planningSummaryMetrics}>
                  <View style={styles.planningSummaryMetric}>
                    <Text style={styles.planningSummaryLabel}>Planes programados</Text>
                    <Text style={styles.planningSummaryValue}>{futurePlansCount}</Text>
                  </View>
                  <View style={styles.planningSummaryMetric}>
                    <Text style={styles.planningSummaryLabel}>Última fecha con plan</Text>
                    <Text numberOfLines={1} style={styles.planningSummaryDate}>{overview?.last_scheduled_date ? dateLabel(overview.last_scheduled_date, { day: "numeric", month: "short", year: "numeric" }) : "Sin fecha"}</Text>
                  </View>
                </View>
                <View style={styles.planningNextPlan}>
                  <Text style={styles.planningSummaryLabel}>Próxima minuta</Text>
                  <View style={styles.planningNextPlanEntity}>
                    <EntityIcon entity="dailyPlan" size="compact" />
                    <View style={styles.planningNextPlanCopy}>
                      <Text numberOfLines={1} style={styles.planningNextPlanName}>{nextScheduledPlan?.plan_name || "Sin próxima minuta"}</Text>
                      <Text style={styles.planningNextPlanDate}>{nextScheduledPlan ? dateLabel(nextScheduledPlan.calendar_date, { day: "numeric", month: "short", year: "numeric" }) : "Sin fecha"}</Text>
                    </View>
                  </View>
                </View>
              </View>
              <View style={styles.commitmentsCardActions}>
                <Pressable accessibilityLabel="Calendarizar" accessibilityRole="button" onPress={() => setPlanMenuVisible(true)} style={({ pressed }) => [styles.commitmentsCardActionChip, styles.commitmentsCardAddButton, pressed && styles.pressed]}>
                  <Plus color={tokens.color.textMain} size={18} strokeWidth={2.1} />
                </Pressable>
                <Pressable accessibilityRole="button" onPress={() => router.push("/calendar/plans" as Href)} style={({ pressed }) => [styles.commitmentsCardActionChip, pressed && styles.pressed]}>
                  <Text adjustsFontSizeToFit numberOfLines={1} style={styles.commitmentsCardActionText}>Ver minutas programadas</Text>
                  <ChevronRight color={tokens.color.textMain} size={18} strokeWidth={2.1} />
                </Pressable>
              </View>
            </Card>
            <Card style={styles.commitmentsCard}>
              <View style={styles.commitmentsCardOverview}>
                <View style={styles.commitmentsCardCopy}>
                  <View style={styles.commitmentsCardHeading}>
                    <Pin color={tokens.color.textMain} size={18} strokeWidth={2.1} />
                    <Text accessibilityRole="header" style={styles.commitmentsCardTitle}>Mis compromisos</Text>
                  </View>
                </View>
                <View accessibilityLabel="Compras, cocinar, entrenamiento y nutricionista" accessible style={styles.commitmentsCardIcons}>
                  {commitmentKinds.map((kind) => {
                    const presentation = commitmentPresentation[kind];
                    const Icon = presentation.icon;
                    return <View key={kind} style={[styles.commitmentsCardIcon, { backgroundColor: `${presentation.color}33` }]}>
                      <Icon color={presentation.color} size={14} strokeWidth={2.1} />
                    </View>;
                  })}
                </View>
              </View>
              <View style={styles.planningSummary}>
                <View style={styles.planningSummaryMetrics}>
                  <View style={styles.planningSummaryMetric}>
                    <Text style={styles.planningSummaryLabel}>Compromisos asignados</Text>
                    <Text style={styles.planningSummaryValue}>{assignedCommitmentsCount}</Text>
                  </View>
                  <View style={styles.planningSummaryMetric}>
                    <Text style={styles.planningSummaryLabel}>Última fecha con compromiso</Text>
                    <Text numberOfLines={1} style={styles.planningSummaryDate}>{lastAssignedCommitmentDate ? dateLabel(lastAssignedCommitmentDate, { day: "numeric", month: "short", year: "numeric" }) : "Sin fecha"}</Text>
                  </View>
                </View>
                <View style={styles.planningNextPlan}>
                  <Text style={styles.planningSummaryLabel}>Próximo compromiso</Text>
                  <View style={styles.planningNextPlanEntity}>
                    {nextAssignedCommitment ? (() => {
                      const presentation = commitmentPresentation[nextAssignedCommitment.kind];
                      const Icon = presentation.icon;
                      return <View style={[styles.commitmentsCardIcon, { backgroundColor: `${presentation.color}33` }]}><Icon color={presentation.color} size={14} strokeWidth={2.1} /></View>;
                    })() : <Pin color={tokens.color.textMuted} size={18} strokeWidth={2.1} />}
                    <View style={styles.planningNextPlanCopy}>
                      <Text numberOfLines={1} style={styles.planningNextPlanName}>{nextAssignedCommitment ? commitmentPresentation[nextAssignedCommitment.kind].label : "Sin próximo compromiso"}</Text>
                      <Text style={styles.planningNextPlanDate}>{nextAssignedCommitment ? dateLabel(nextAssignedCommitment.calendar_date, { day: "numeric", month: "short", year: "numeric" }) : "Sin fecha"}</Text>
                    </View>
                  </View>
                </View>
              </View>
              <View style={styles.commitmentsCardActions}>
                <Pressable accessibilityLabel="Agregar nuevo compromiso" accessibilityRole="button" onPress={() => setCommitmentMenuVisible(true)} style={({ pressed }) => [styles.commitmentsCardActionChip, styles.commitmentsCardAddButton, pressed && styles.pressed]}>
                  <Plus color={tokens.color.textMain} size={18} strokeWidth={2.1} />
                </Pressable>
                <Pressable accessibilityLabel="Ver compromisos" accessibilityRole="button" onPress={() => router.push("/calendar/registry" as Href)} style={({ pressed }) => [styles.commitmentsCardActionChip, pressed && styles.pressed]}>
                  <Text adjustsFontSizeToFit numberOfLines={1} style={styles.commitmentsCardActionText}>Ver compromisos</Text>
                  <ChevronRight color={tokens.color.textMain} size={18} strokeWidth={2.1} />
                </Pressable>
              </View>
            </Card>
          </View>
          <ProgramSectionHeader icon={CalendarDays} subtitle="Los próximos siete días, con o sin plan asignado." title="Próximas minutas" />
          <View style={styles.upcomingMetricsSpacing}>
            <CalendarWeekMetrics days={upcoming} weightKg={profile?.current_weight_kg ?? null} />
          </View>
          <View style={styles.upcomingPanelsSpacing}>
            <CalendarUpcomingPanels days={upcoming} localDate={overview?.local_date ?? ""} onAssign={assignUpcomingDay} onOpenDay={openUpcomingDay} onRemove={removeUpcomingDay} onReorder={reorderUpcomingDays} onReplace={replaceUpcomingDay} weightKg={profile?.current_weight_kg ?? null} />
          </View>
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
            {!selectedDetail && !error ? <View style={styles.weekDayLoading}><LoadingState label="Abriendo esta fecha…" mode="content" /></View> : selectedDetail?.has_plan && selectedDetail.plan_snapshot ? (
              <CalendarizedDailyPlanCard
                apiRequest={apiRequest}
                dateLabel={compactDate(selectedDetail.calendar_date)}
                dayId={selectedDetail.id}
                eyebrow={selectedDetail.source_program_name ?? "PLAN DE CALENDARIO"}
                mealExecution={selectedDetail.meal_execution}
                onAddMeal={selectedDayId != null ? () => router.push(pickerHref("meal-to-calendarized-day", { dayId: selectedDayId, returnTo: "/calendar" })) : undefined}
                onChanged={async () => { setDetail(await apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${selectedDetail.calendar_date}`)); }}
                planName={selectedDetail.plan_name}
                snapshot={selectedDetail.plan_snapshot}
              />
            ) : selectedDetail ? <InlineNotice>No hay un plan asignado a esta fecha.</InlineNotice> : null}
          </ProgramDaySelector>
          {selectedDetail && !selectedDetail.has_execution && !selectedDetail.has_plan ? <Button label="Asignar plan a esta fecha" onPress={() => openDay(selectedDetail.calendar_date)} variant="secondary" /> : null}

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
        <View style={styles.futureWeekMetrics}>
          <CalendarWeekMetrics days={fullCalendarWeeks.get(calendarWeek.key) ?? calendarWeek.days} weightKg={profile?.current_weight_kg ?? null} />
        </View>
        <View style={styles.futureWeekPanel}>
          <CalendarUpcomingPanels days={calendarWeek.days} localDate={overview?.local_date ?? ""} onAssign={assignUpcomingDay} onOpenDay={openUpcomingDay} onRemove={removeUpcomingDay} onReorder={reorderUpcomingDays} onReplace={replaceUpcomingDay} weightKg={profile?.current_weight_kg ?? null} />
        </View>
      </View>) : null}
    </Screen>
    <CalendarizeActions onClose={() => setCalendarMenuVisible(false)} visible={calendarMenuVisible} />
    <ActionSheetModal onRequestClose={() => setCommitmentMenuVisible(false)} visible={commitmentMenuVisible}>
      <SafeAreaView edges={["left", "right"]} style={styles.progressSheet}>
        <ActionSheetHeader icon={Pin} onClose={() => setCommitmentMenuVisible(false)} title="Registrar compromiso" />
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
  calendarBlock: { gap: 0, marginTop: 18 },
  calendarizeActions: { gap: tokens.spacing.sm },
  commitmentsCard: { gap: tokens.spacing.sm, marginHorizontal: -12, paddingBottom: tokens.card.outerPadding - 6, paddingTop: tokens.card.outerPadding - 4 },
  commitmentsCardActionChip: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, flexDirection: "row", gap: 4, height: 40, justifyContent: "center", paddingHorizontal: tokens.spacing.md },
  commitmentsCardActionText: { color: tokens.color.textMain, fontSize: 13, fontWeight: tokens.weight.semibold },
  commitmentsCardAddButton: { borderRadius: 20, paddingHorizontal: 0, width: 40 },
  commitmentsCardActions: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "space-between", marginHorizontal: -6, marginTop: 8 },
  commitmentsCardCopy: { flex: 1 },
  commitmentsCardHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  commitmentsCardIcon: { alignItems: "center", borderRadius: 8, height: 24, justifyContent: "center", width: 24 },
  commitmentsCardIcons: { flexDirection: "row", gap: 5 },
  commitmentsCardOverview: { alignItems: "flex-start", flexDirection: "row", justifyContent: "space-between" },
  commitmentsCardTitle: { color: tokens.color.textMain, fontSize: 16, fontWeight: tokens.weight.semibold },
  content: { gap: tokens.spacing.lg },
  futureWeekPanel: { marginTop: 0 },
  futureWeekMetrics: { marginBottom: tokens.spacing.lg - 6, marginTop: tokens.spacing.md - 18 },
  futureWeekSection: { gap: 0 },
  futureWeekSpacing: { marginTop: 18 },
  progressMenuButton: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: 18, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  progressHeaderSpacing: { marginTop: -42 },
  progressDateHelp: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  progressSheet: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  progressSheetContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  planningNextPlan: { borderTopColor: tokens.color.borderSoft, borderTopWidth: StyleSheet.hairlineWidth, gap: tokens.spacing.xs, paddingTop: tokens.spacing.sm },
  planningNextPlanCopy: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "space-between" },
  planningNextPlanDate: { color: tokens.color.textMain, fontSize: 12, fontWeight: tokens.weight.semibold },
  planningNextPlanEntity: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  planningNextPlanName: { color: tokens.color.textMain, flex: 1, fontSize: 13, fontWeight: tokens.weight.semibold },
  planningSummary: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, gap: tokens.spacing.sm, marginHorizontal: -6, marginTop: 4, padding: tokens.spacing.sm + 6 },
  planningSummaryDate: { color: tokens.color.textMain, fontSize: 14, fontWeight: tokens.weight.bold, marginTop: 3 },
  planningSummaryLabel: { color: tokens.color.textMuted, fontSize: 11 },
  planningSummaryMetric: { flex: 1 },
  planningSummaryMetrics: { flexDirection: "row", gap: tokens.spacing.md },
  planningSummaryValue: { color: tokens.color.textMain, fontSize: 20, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, marginTop: 2 },
  upcomingPanelsSpacing: { marginTop: -20 },
  upcomingMetricsSpacing: { marginBottom: 10, marginTop: -20 },
  stickyHeader: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, paddingTop: tokens.spacing.sm },
  todayCard: { gap: tokens.spacing.sm, marginHorizontal: -6 },
  todayCommitmentColumn: { flex: 1, gap: tokens.spacing.sm, minWidth: 0 },
  todayCommitmentColumns: { flexDirection: "row", gap: tokens.spacing.sm },
  todayCommitmentIcon: { alignItems: "center", borderRadius: 7, height: 22, justifyContent: "center", width: 22 },
  todayDetailButton: { marginHorizontal: -6 },
  todayEmpty: { color: tokens.color.textMuted, fontSize: 14 },
  todayRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, minHeight: 32 },
  todayRowTitle: { color: tokens.color.textMain, flex: 1, fontSize: 14, fontWeight: "600" },
  todaySection: { gap: tokens.spacing.sm, marginTop: 8 },
  upcomingCommitmentsDashboard: { flexDirection: "row", gap: tokens.spacing.xs, marginHorizontal: -6 },
  upcomingCommitmentsHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  upcomingCommitmentsIcon: { alignItems: "center", borderRadius: 8, height: 24, justifyContent: "center", width: 24 },
  upcomingCommitmentsMetric: { alignItems: "center", borderRadius: tokens.radius.md, flex: 1, gap: 3, minWidth: 0, paddingHorizontal: 3, paddingVertical: tokens.spacing.sm + 4 },
  upcomingCommitmentsMetricValueRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  upcomingCommitmentsSection: { gap: tokens.spacing.sm },
  upcomingCommitmentsTitle: { color: tokens.color.textMain, fontSize: 15, fontWeight: tokens.weight.semibold },
  upcomingCommitmentsValue: { color: tokens.color.textMain, fontSize: 18, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold },
  weekDayLoading: { minHeight: 220 },
  pressed: { opacity: 0.65 },
});
