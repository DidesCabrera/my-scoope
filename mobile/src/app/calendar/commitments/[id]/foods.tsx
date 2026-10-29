import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { Check, ChevronLeft, ChevronRight, List, Pencil } from "lucide-react-native";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarCommitment, CalendarDayDetailData, CalendarOverviewData, CalendarPeriodFoodsData } from "@/api/calendar-types";
import { useSession } from "@/auth/session-context";
import { commitmentFoodPanelItem, commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { commitmentDotKinds } from "@/components/calendarization/calendar-commitment-dots";
import { calendarFoodDayRole, selectCalendarFoodDate, validCalendarFoodPeriod } from "@/components/calendarization/calendar-food-period";
import { isCurrentMonthFromToday, monthKeyFromDate, monthLabel, monthWindow, shiftMonth } from "@/components/calendarization/calendar-month";
import { createCalendarMonthCache } from "@/components/calendarization/calendar-month-cache";
import { CalendarTodayOutline } from "@/components/calendarization/calendar-today-outline";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { GroupedFoodsCard } from "@/components/panels";
import { Button, Chip, InlineNotice, LoadingState, Screen, SectionPageHeader } from "@/components/ui";
import { tokens } from "@/design/tokens";

function shortDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

export default function CommitmentFoodsScreen() {
  const { id, date } = useLocalSearchParams<{ id: string; date: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const monthCache = useMemo(() => createCalendarMonthCache(apiRequest), [apiRequest]);
  const [commitment, setCommitment] = useState<CalendarCommitment | null>(null);
  const [month, setMonth] = useState<string | null>(null);
  const [overview, setOverview] = useState<CalendarOverviewData | null>(null);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [preview, setPreview] = useState<CalendarPeriodFoodsData | null>(null);
  const [todaySize, setTodaySize] = useState({ width: 0, height: 0 });
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [associating, setAssociating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      fallback: id && date ? `/calendar/commitments/${id}?date=${date}` as Href : "/calendar/registry",
      identityVisible: compactHeaderVisible,
      mode: "back",
      title: "Generar lista de alimentos",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, date, id, setHeaderPresentation]));

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated" || !date || !/^\d{4}-\d{2}-\d{2}$/.test(date) || !id) return;
    let active = true;
    setLoading(true);
    setError(null);
    void apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${date}`)
      .then((day) => {
        if (!active) return;
        const found = day.commitments?.find((item) => item.id === Number(id)) ?? null;
        setCommitment(found);
        if (!found) { setError("Este compromiso ya no está registrado en esta fecha."); return; }
        const initialStart = found.food_period_start ?? "";
        const initialEnd = found.food_period_end ?? "";
        setStart(initialStart);
        setEnd(initialEnd);
        setMonth(monthKeyFromDate(initialStart || date));
        setPreview(null);
      })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, date, id, status]));

  useEffect(() => {
    if (status !== "authenticated" || !month) return;
    let active = true;
    void monthCache.load(month)
      .then((result) => { if (active) setOverview(result); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); });
    return () => { active = false; };
  }, [month, monthCache, status]);

  const monthDates = useMemo(() => {
    if (!month) return [];
    const window = monthWindow(month);
    const first = new Date(`${window.startDate}T12:00:00Z`);
    return Array.from({ length: window.days }, (_, index) => new Date(first.getTime() + index * 86_400_000).toISOString().slice(0, 10));
  }, [month]);
  const monthDaysByDate = new Map(overview?.start_date === (month ? monthWindow(month).startDate : "")
    ? overview.days.map((day) => [day.calendar_date, day] as const) : []);

  function changeMonth(delta: number) {
    if (!month || calculating || associating) return;
    const nextMonth = shiftMonth(month, delta);
    const cached = monthCache.get(nextMonth);
    if (cached) setOverview(cached);
    setMonth(nextMonth);
  }

  function selectDay(day: string) {
    if (calculating || associating) return;
    const next = selectCalendarFoodDate(start, end, day);
    if (next.tooLong) { setError("Elige un periodo de hasta 366 días."); return; }
    setStart(next.start);
    setEnd(next.end);
    setPreview(null);
    setError(null);
  }

  function clearPeriod() {
    if (calculating || associating) return;
    setStart("");
    setEnd("");
    setPreview(null);
    setError(null);
  }

  async function generatePreview() {
    if (!validCalendarFoodPeriod(start, end) || calculating) return;
    setCalculating(true);
    setError(null);
    try {
      const result = await apiRequest<CalendarPeriodFoodsData>(`/api/v1/calendar/foods?start_date=${start}&end_date=${end}`);
      setPreview(result);
    } catch (nextError) { setError(userFacingError(nextError)); }
    finally { setCalculating(false); }
  }

  async function associateList() {
    if (!commitment || !preview || associating) return;
    setAssociating(true);
    setError(null);
    try {
      await apiRequest<CalendarCommitment>(`/api/v1/calendar/commitments/${commitment.id}`, {
        method: "PATCH",
        body: JSON.stringify({ update_food_period: true, food_period_start: start, food_period_end: end }),
      });
      Alert.alert("Lista asociada con éxito", undefined, [{ text: "Aceptar", onPress: () => router.back() }]);
    } catch (nextError) { setError(userFacingError(nextError)); }
    finally { setAssociating(false); }
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date) || !id) return <Redirect href="/calendar" />;
  if (loading) return <LoadingState label="Preparando la lista de alimentos…" />;
  if (!commitment) return <Screen headerMode="preserve"><InlineNotice tone="error">{error ?? "No encontramos este compromiso."}</InlineNotice></Screen>;

  const controlsLocked = calculating || associating;
  return <Screen contentStyle={styles.content} headerMode="preserve" onHeaderVisibilityChange={setCompactHeaderVisible}>
    <SectionPageHeader icon={<List color={tokens.color.textMain} size={28} strokeWidth={1.8} />} section="calendarization" subtitle="Selecciona la fecha de inicio y término del periodo" title="Generar lista de alimentos" />
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    <View style={styles.periodSection}>
      <View style={styles.monthNavigation}>
        <Pressable accessibilityLabel="Mes anterior del periodo" accessibilityRole="button" disabled={controlsLocked} onPress={() => changeMonth(-1)} style={styles.monthArrow}><ChevronLeft color={tokens.color.textMain} size={20} /></Pressable>
        <Text accessibilityRole="header" style={styles.monthTitle}>{month ? monthLabel(month) : ""}</Text>
        <Pressable accessibilityLabel="Mes siguiente del periodo" accessibilityRole="button" disabled={controlsLocked} onPress={() => changeMonth(1)} style={styles.monthArrow}><ChevronRight color={tokens.color.textMain} size={20} /></Pressable>
      </View>
      <View style={[styles.grid, styles.periodGrid]}>
        {(["L", "M", "M", "J", "V", "S", "D"] as const).map((label, index) => <Text key={`weekday-${index}`} style={styles.gridHeader}>{label}</Text>)}
        {monthDates.map((day) => {
          const role = calendarFoodDayRole(day, start, end);
          const endpoint = role === "start" || role === "end" || role === "single";
          const dayData = monthDaysByDate.get(day);
          const dots = commitmentDotKinds(dayData?.commitments);
          const accent = tokens.color.food;
          return <Pressable
            accessibilityLabel={`${shortDate(day)}: ${role === "single" ? "inicio y término" : role === "start" ? "inicio" : role === "end" ? "término" : role === "between" ? "dentro del periodo" : "fuera del periodo"}`}
            accessibilityRole="button"
            disabled={controlsLocked}
            key={day}
            onLayout={day === overview?.local_date ? ({ nativeEvent: { layout } }) => setTodaySize((current) => current.width === layout.width && current.height === layout.height ? current : { width: layout.width, height: layout.height }) : undefined}
            onPress={() => selectDay(day)}
            style={[styles.gridDate, dayData?.has_plan && styles.gridDateFilled, dayData?.has_plan && isCurrentMonthFromToday(day, overview?.local_date) && styles.gridDateUpcomingFilled, endpoint && { backgroundColor: `${accent}26`, borderColor: accent }, role === "between" && { backgroundColor: `${accent}33` }, monthKeyFromDate(day) !== month && styles.gridDateAdjacent, day === overview?.local_date && styles.gridDateToday]}>
            <Text style={[styles.gridNumber, dayData?.has_plan && styles.gridNumberWithPlan, Boolean(overview?.local_date && day < overview.local_date) && styles.gridNumberPast, endpoint && { color: accent, fontWeight: "700" }, role === "between" && { color: accent }]}>{day.slice(8, 10)}</Text>
            {dots.length ? <View style={[styles.commitmentDots, Boolean(overview?.local_date && day < overview.local_date) && styles.commitmentDotsPast, day === overview?.local_date && styles.commitmentDotsToday]}>{dots.map((kind) => <View key={kind} style={[styles.commitmentDot, { backgroundColor: commitmentPresentation[kind].color }]} />)}</View> : null}
            {day === overview?.local_date ? <CalendarTodayOutline {...todaySize} /> : null}
          </Pressable>;
        })}
      </View>
      {!preview ? <View style={styles.periodActions}>
        <Button disabled={!validCalendarFoodPeriod(start, end) || controlsLocked} label="Generar lista de alimentos" loading={calculating} onPress={() => void generatePreview()} />
        <Button disabled={!start && !end || controlsLocked} label="Limpiar selección" onPress={clearPeriod} variant="secondary" />
      </View> : null}
    </View>
    {preview ? <>
      <View style={styles.confirmActions}>
        <Button contentStyle={styles.confirmButtonContent} icon={<Check color={tokens.color.surfaceApp} size={18} strokeWidth={2.6} />} label="Asociar lista de alimentos" loading={associating} onPress={() => void associateList()} />
        <Button contentStyle={styles.confirmButtonContent} disabled={associating} icon={<Pencil color={tokens.color.textMain} size={18} strokeWidth={2.2} />} label="Editar periodo" onPress={() => setPreview(null)} variant="secondary" />
      </View>
      <GroupedFoodsCard
        intro={<Chip backgroundColor={`${tokens.color.food}1A`} borderColor={tokens.color.food} label={`${shortDate(start)} – ${shortDate(end)}`} textColor={tokens.color.textMain} />}
        items={preview.foods.map(commitmentFoodPanelItem)}
        preparationFirst={commitment.kind === "shopping"}
        showContents
        summaryChips={<Chip backgroundColor={`${tokens.color.dailyPlan}1A`} borderColor={tokens.color.dailyPlan} label={`${preview.plans_count} ${preview.plans_count === 1 ? "plan" : "planes"}`} textColor={tokens.color.textMain} />}
        title={commitment.kind === "cooking" ? "Alimentos para cocinar" : "Alimentos para comprar"}
      />
    </> : null}
  </Screen>;
}

const styles = StyleSheet.create({
  commitmentDot: { borderRadius: 3, height: 5, width: 5 },
  commitmentDots: { bottom: 4, flexDirection: "row", gap: 2, position: "absolute" },
  commitmentDotsPast: { opacity: 0.5 },
  commitmentDotsToday: { bottom: 6 },
  confirmActions: { gap: tokens.spacing.sm, marginBottom: 28 - tokens.spacing.lg },
  confirmButtonContent: { transform: [{ translateX: -10 }] },
  content: { gap: tokens.spacing.lg },
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: tokens.spacing.sm },
  gridDate: { alignItems: "center", borderColor: "transparent", borderRadius: 10, borderWidth: 2, justifyContent: "center", minHeight: 40, width: "13.5%" },
  gridDateAdjacent: { opacity: 0.5 },
  gridDateFilled: { backgroundColor: `${tokens.color.dailyPlan}2E` },
  gridDateToday: { borderWidth: 0 },
  gridDateUpcomingFilled: { backgroundColor: `${tokens.color.dailyPlan}59` },
  gridHeader: { color: tokens.color.textMuted, fontSize: 11, textAlign: "center", width: "13.5%" },
  gridNumber: { color: tokens.color.textMain, fontSize: 14, fontWeight: "500" },
  gridNumberPast: { opacity: 0.8 },
  gridNumberWithPlan: { color: tokens.color.textMain, fontWeight: "700" },
  monthArrow: { alignItems: "center", height: 36, justifyContent: "center", width: 36 },
  monthNavigation: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: tokens.spacing.md },
  monthTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: "600" },
  periodActions: { gap: tokens.spacing.sm },
  periodGrid: { marginBottom: 34 - tokens.spacing.lg },
  periodSection: { gap: tokens.spacing.lg },
});
