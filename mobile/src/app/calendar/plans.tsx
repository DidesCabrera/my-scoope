import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { CalendarDays, ClipboardList, Pin } from "lucide-react-native";
import { useCallback, useEffect, useMemo, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarDay, CalendarOverviewData } from "@/api/calendar-types";
import type { CalendarDayDetailData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarDaySectionHeading } from "@/components/calendarization/calendar-day-section-heading";
import { CalendarMonthCalendar } from "@/components/calendarization/calendar-month-calendar";
import { createCalendarMonthCache } from "@/components/calendarization/calendar-month-cache";
import { monthKeyFromDate, shiftMonth } from "@/components/calendarization/calendar-month";
import { CalendarUpcomingPanels } from "@/components/calendarization/calendar-upcoming-panels";
import { CalendarWeekMetrics } from "@/components/calendarization/calendar-week-metrics";
import { CalendarizedDailyPlanCard } from "@/components/calendarization/calendarized-daily-plan-card";
import { CalendarizeActions } from "@/components/calendarization/calendarize-actions";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { pickerHref } from "@/components/pickers/picker-routes";
import { ProgramSectionHeader } from "@/components/programs/program-section-header";
import { Button, Card, InlineNotice, LoadingState, Screen, SectionPageHeader } from "@/components/ui";
import { tokens } from "@/design/tokens";

function compactDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" })
    .format(new Date(`${value}T12:00:00`));
}

export default function ScheduledPlansScreen() {
  const router = useRouter();
  const setHeaderPresentation = useHeaderPresentation();
  const { apiRequest, profile, status } = useSession();
  const monthCache = useMemo(() => createCalendarMonthCache(apiRequest), [apiRequest]);
  const [overview, setOverview] = useState<CalendarOverviewData | null>(null);
  const [upcomingOverview, setUpcomingOverview] = useState<CalendarOverviewData | null>(null);
  const [localToday, setLocalToday] = useState<string | null>(null);
  const [visibleMonth, setVisibleMonth] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<CalendarDayDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [calendarMenuVisible, setCalendarMenuVisible] = useState(false);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      action: { icon: "plus", label: "Calendarizar", onPress: () => setCalendarMenuVisible(true) },
      fallback: "/calendar",
      identityVisible: compactHeaderVisible,
      mode: "back",
      title: "Mis minutas programadas",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, setHeaderPresentation]));

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated") return;
    let active = true;
    void apiRequest<CalendarOverviewData>("/api/v1/calendar?days=35")
      .then((data) => {
        if (!active) return;
        setUpcomingOverview(data);
        setLocalToday(data.local_date);
        setVisibleMonth((current) => current ?? monthKeyFromDate(data.local_date));
        setSelectedDate((current) => current ?? data.local_date);
      })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); });
    return () => { active = false; };
  }, [apiRequest, status]));

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated" || !visibleMonth) return;
    let active = true;
    const cached = monthCache.get(visibleMonth);
    if (cached) setOverview(cached);
    setLoading(!cached);
    setError(null);
    void monthCache.load(visibleMonth)
      .then((data) => { if (active) setOverview(data); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [monthCache, status, visibleMonth]));

  const monthDays = useMemo(() => overview?.days ?? [], [overview]);
  const selectedDay = monthDays.find((day) => day.calendar_date === selectedDate);
  const upcoming = useMemo(() => {
    if (!upcomingOverview) return [];
    return upcomingOverview.days.filter((day) => day.calendar_date >= upcomingOverview.local_date).slice(0, 7);
  }, [upcomingOverview]);
  const futurePlansCount = upcomingOverview?.future_plans_count ?? 0;

  useEffect(() => {
    if (!selectedDate || !selectedDay?.has_plan || status !== "authenticated") return;
    let active = true;
    void apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${selectedDate}`)
      .then((detail) => { if (active) setSelectedDetail(detail); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
    return () => { active = false; };
  }, [apiRequest, selectedDate, selectedDay?.has_plan, status]);

  const refreshDetail = useCallback(async (date: string) => {
    const next = await apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${date}`);
    setSelectedDetail(next);
  }, [apiRequest]);

  const refreshCalendars = useCallback(async () => {
    const nextUpcoming = await apiRequest<CalendarOverviewData>("/api/v1/calendar?days=35");
    setUpcomingOverview(nextUpcoming);
    if (visibleMonth) {
      monthCache.invalidate([visibleMonth]);
      setOverview(await monthCache.load(visibleMonth));
    }
  }, [apiRequest, monthCache, visibleMonth]);

  function changeMonth(delta: number) {
    if (!visibleMonth) return;
    const nextMonth = shiftMonth(visibleMonth, delta);
    setVisibleMonth(nextMonth);
    setSelectedDate(`${nextMonth}-01`);
  }

  function renderSelectedPlan(day: CalendarDay) {
    const detail = selectedDetail;
    if (!detail?.plan_snapshot || detail.calendar_date !== day.calendar_date) return <Card><LoadingState label="Abriendo minuta…" mode="content" /></Card>;
    const dayId = detail.id;
    return <CalendarizedDailyPlanCard
      apiRequest={apiRequest}
      dateLabel={compactDate(day.calendar_date)}
      dayId={detail.id}
      eyebrow={detail.source_program_name ?? "MINUTA DIARIA"}
      mealExecution={detail.meal_execution}
      onAddMeal={dayId != null ? () => router.push(pickerHref("meal-to-calendarized-day", { dayId, returnTo: "/calendar/plans" })) : undefined}
      onChanged={() => refreshDetail(day.calendar_date)}
      planName={detail.plan_name}
      snapshot={detail.plan_snapshot}
    />;
  }

  function openUpcomingDay(day: CalendarDay) {
    if (day.has_plan && day.id != null) router.push(`/program/days/${day.id}` as Href);
    else router.push(`/calendar/days/${day.calendar_date}` as Href);
  }

  async function removeUpcomingDay(day: CalendarDay) {
    setError(null);
    try {
      await apiRequest(`/api/v1/calendar/days/${day.calendar_date}/plan`, { method: "DELETE" });
      await refreshCalendars();
    } catch (nextError) {
      setError(userFacingError(nextError));
      throw nextError;
    }
  }

  async function reorderUpcomingDays(dates: string[], orderedDayIds: (number | null)[]) {
    setError(null);
    try {
      await apiRequest("/api/v1/calendar/reorder", { body: JSON.stringify({ dates, ordered_day_ids: orderedDayIds }), method: "PUT" });
      await refreshCalendars();
    } catch (nextError) {
      setError(userFacingError(nextError));
      throw nextError;
    }
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !overview) return <LoadingState label="Preparando tus minutas programadas…" />;

  return <>
    <Screen contentStyle={styles.content} headerMode="preserve" onHeaderVisibilityChange={setCompactHeaderVisible} scrollHeader={<SectionPageHeader icon={<Pin color={tokens.color.textMain} size={28} strokeWidth={1.8} />} section="calendarization" subtitle="Revisa las minutas asignadas a cada fecha." title="Mis minutas programadas" />}>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      <View style={styles.summarySection}>
        <View accessibilityLabel={`${futurePlansCount} minutas programadas`} accessible style={styles.summaryMetric}>
          <View style={styles.summaryIcon}>
            <ClipboardList color={tokens.color.entityIconForeground} size={19} strokeWidth={2.1} />
          </View>
          <View style={styles.summaryCopy}>
            <Text style={styles.summaryValue}>{futurePlansCount}</Text>
            <Text style={styles.summaryLabel}>Minutas programadas</Text>
          </View>
        </View>
      </View>
      <View style={styles.calendarHeading}>
        <CalendarDays color={tokens.color.textMain} size={18} strokeWidth={2.1} />
        <Text accessibilityRole="header" style={styles.calendarTitle}>Calendario de minutas</Text>
      </View>
      {visibleMonth && overview ? <CalendarMonthCalendar days={monthDays} error={error} localDate={localToday ?? overview.local_date} onChangeMonth={changeMonth} onOpenDay={setSelectedDate} onReturnToCurrentMonth={() => setVisibleMonth(monthKeyFromDate(overview.local_date))} selectedDate={selectedDate ?? undefined} visibleMonth={visibleMonth} /> : null}
      {selectedDate && localToday ? <View style={styles.selectedSection}>
        <CalendarDaySectionHeading date={selectedDate} today={localToday} />
        {selectedDay?.has_plan ? renderSelectedPlan(selectedDay) : <Card><Text style={styles.empty}>No hay una minuta programada para este día.</Text></Card>}
      </View> : null}
      <ProgramSectionHeader icon={CalendarDays} subtitle="Los próximos siete días, con o sin plan asignado." title="Próximas minutas" />
      <View style={styles.upcomingMetricsSpacing}>
        <CalendarWeekMetrics days={upcoming} weightKg={profile?.current_weight_kg ?? null} />
      </View>
      <View style={styles.upcomingPanelsSpacing}>
        <CalendarUpcomingPanels
          days={upcoming}
          localDate={localToday ?? ""}
          onAssign={(day) => router.push({ pathname: "/calendar/days/[date]", params: { date: day.calendar_date, section: "assign" } } as Href)}
          onOpenDay={openUpcomingDay}
          onRemove={removeUpcomingDay}
          onReorder={reorderUpcomingDays}
          onReplace={(day) => router.push({ pathname: "/calendar/days/[date]", params: { date: day.calendar_date, section: "replace" } } as Href)}
          weightKg={profile?.current_weight_kg ?? null}
        />
      </View>
      <Button label="Ver más fechas" onPress={() => router.push("/calendar/future" as Href)} variant="secondary" />
    </Screen>
    <CalendarizeActions onClose={() => setCalendarMenuVisible(false)} visible={calendarMenuVisible} />
  </>;
}

const styles = StyleSheet.create({
  calendarHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  calendarTitle: { color: tokens.color.textMain, fontSize: 16, fontWeight: tokens.weight.bold },
  content: { gap: tokens.spacing.lg },
  empty: { color: tokens.color.textMuted, fontSize: 13 },
  selectedSection: { gap: tokens.spacing.sm },
  summaryCopy: { gap: 0 },
  summaryIcon: { alignItems: "center", backgroundColor: tokens.color.dailyPlan, borderRadius: 11, height: 38, justifyContent: "center", width: 38 },
  summaryLabel: { color: tokens.color.textMuted, fontSize: 11, lineHeight: 14 },
  summaryMetric: { alignItems: "center", alignSelf: "flex-start", flexDirection: "row", gap: tokens.spacing.sm },
  summarySection: { gap: tokens.spacing.sm },
  summaryValue: { color: tokens.color.textMain, fontSize: 20, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, lineHeight: 22 },
  upcomingMetricsSpacing: { marginBottom: 10, marginTop: -20 },
  upcomingPanelsSpacing: { marginTop: -20 },
});
