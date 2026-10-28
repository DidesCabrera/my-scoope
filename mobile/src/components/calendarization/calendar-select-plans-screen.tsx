import * as Crypto from "expo-crypto";
import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronLeft, ChevronRight, Pin } from "lucide-react-native";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarDay, CalendarDayDetailData, CalendarOverviewData, LibraryItem, LibraryPageData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { DailyPlanPreviewCard } from "@/components/calendarization/daily-plan-preview-card";
import { commitmentDotKinds } from "@/components/calendarization/calendar-commitment-dots";
import { commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { CalendarTodayOutline } from "@/components/calendarization/calendar-today-outline";
import { monthKeyFromDate, monthLabel, monthWindow, shiftMonth } from "@/components/calendarization/calendar-month";
import { createCalendarMonthCache } from "@/components/calendarization/calendar-month-cache";
import { snapshotMealPanelItem } from "@/components/calendarization/presentation-adapters";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { internalHref } from "@/navigation/internal-href";
import { NutritionEntityCard } from "@/components/nutrition";
import { PickerEntryTabs } from "@/components/pickers/picker-entry-tabs";
import { MealPanels as SnapshotMealPanels } from "@/components/panels";
import { Button, InlineNotice, LoadingState, Screen, SearchField, SectionHeading } from "@/components/ui";
import { ConfirmationState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";

function readableDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

function emptyMonthOverview(month: string, localToday: string): CalendarOverviewData {
  const { startDate, days } = monthWindow(month);
  const start = new Date(`${startDate}T12:00:00Z`);
  const dates = Array.from({ length: days }, (_, offset) => {
    const date = new Date(start);
    date.setUTCDate(start.getUTCDate() + offset);
    return date.toISOString().slice(0, 10);
  });
  return {
    local_date: localToday,
    start_date: startDate,
    end_date: dates[dates.length - 1],
    days: dates.map((calendar_date) => ({ id: null, calendar_date, has_plan: false, plan_name: "", source_kind: null, source_program_name: null, has_execution: false })),
  };
}

function calendarDayNutrition(day: CalendarDay) {
  const protein = day.plan_protein_grams ?? 0;
  const carbs = day.plan_carbs_grams ?? 0;
  const fat = day.plan_fat_grams ?? 0;
  const macroCalories = protein * 4 + carbs * 4 + fat * 9;
  const allocation = (calories: number) => macroCalories > 0 ? calories / macroCalories * 100 : 0;
  return {
    calories: day.plan_calories ?? macroCalories,
    protein: { allocation: allocation(protein * 4), grams: protein, perKilogram: day.plan_protein_per_kilogram },
    carbs: { allocation: allocation(carbs * 4), grams: carbs },
    fat: { allocation: allocation(fat * 9), grams: fat },
  };
}

export default function SelectCalendarPlansScreen() {
  const router = useRouter();
  const { dailyPlanId, origin, returnTo } = useLocalSearchParams<{ dailyPlanId?: string; origin?: string; returnTo?: string }>();
  const initialPlanId = (origin === "onboarding" || origin === "detail" || origin === "library") && Number.isInteger(Number(dailyPlanId)) && Number(dailyPlanId) > 0 ? Number(dailyPlanId) : null;
  const onboardingPlanId = origin === "onboarding" ? initialPlanId : null;
  const returnHref: Href = origin === "detail" || origin === "library" ? (internalHref(returnTo) ?? "/calendar") : onboardingPlanId ? "/onboarding" : origin === "home" ? "/today" : "/calendar";
  const { apiRequest, status } = useSession();
  const monthCache = useMemo(() => createCalendarMonthCache(apiRequest), [apiRequest]);
  const setHeaderPresentation = useHeaderPresentation();
  const [plans, setPlans] = useState<LibraryItem[]>([]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<LibraryItem | null>(null);
  const [localToday, setLocalToday] = useState("");
  const [selectedDates, setSelectedDates] = useState<string[]>([]);
  const [todaySize, setTodaySize] = useState({ width: 0, height: 0 });
  const [selectedDaysByDate, setSelectedDaysByDate] = useState<Record<string, CalendarDay>>({});
  const [replacementDetailsByDate, setReplacementDetailsByDate] = useState<Record<string, CalendarDayDetailData>>({});
  const [visibleMonth, setVisibleMonth] = useState("");
  const [monthOverview, setMonthOverview] = useState<CalendarOverviewData | null>(null);
  const [monthLoading, setMonthLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [confirmReplacement, setConfirmReplacement] = useState<CalendarDayDetailData[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selectedDateList = useMemo(() => [...selectedDates].sort(), [selectedDates]);
  const replacementDays = useMemo(() => selectedDateList
    .map((selectedDate) => selectedDaysByDate[selectedDate])
    .filter((day): day is CalendarDay => Boolean(day?.has_plan)), [selectedDateList, selectedDaysByDate]);

  useFocusEffect(useCallback(() => {
    const cancel = () => router.dismissTo(returnHref as Href);
    setHeaderPresentation({
      action: selected ? undefined : { label: "Cancelar", onPress: cancel },
      fallback: returnHref,
      leadingAction: selected ? initialPlanId
        ? { icon: "back", label: "Volver", onPress: cancel }
        : { icon: "back", label: "Volver a los planes", onPress: () => { setSelected(null); setConfirmReplacement(null); setError(null); } } : undefined,
      mode: "back",
      title: selected ? "Calendarizar minuta" : "Seleccionar plan individual",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [initialPlanId, returnHref, router, selected, setHeaderPresentation]));

  useEffect(() => {
    if (status !== "authenticated" || !initialPlanId) return;
    let active = true;
    void apiRequest<LibraryItem>(`/api/v1/library/daily-plans/${initialPlanId}`)
      .then((plan) => { if (active) setSelected(plan); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); });
    return () => { active = false; };
  }, [apiRequest, initialPlanId, status]);

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated") return;
    let active = true;
    void apiRequest<CalendarOverviewData>("/api/v1/calendar?days=1")
      .then((overview) => {
        if (!active) return;
        setLocalToday(overview.local_date);
        const today = overview.days.find((day) => day.calendar_date === overview.local_date);
        if (today) setSelectedDaysByDate((current) => ({ ...current, [today.calendar_date]: today }));
        setVisibleMonth((current) => current || monthKeyFromDate(overview.local_date));
      })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); });
    return () => { active = false; };
  }, [apiRequest, status]));

  useEffect(() => {
    if (status !== "authenticated" || !selected || !visibleMonth) return;
    let active = true;
    void monthCache.load(visibleMonth)
      .then((overview) => {
        if (!active) return;
        setMonthOverview(overview);
        setMonthLoading(false);
        void monthCache.load(shiftMonth(visibleMonth, 1)).catch(() => undefined);
        setSelectedDaysByDate((current) => {
          const next = { ...current };
          for (const day of overview.days) if (current[day.calendar_date]) next[day.calendar_date] = day;
          return next;
        });
      })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); });
    return () => { active = false; };
  }, [monthCache, selected, status, visibleMonth]);

  useEffect(() => {
    if (status !== "authenticated") return;
    const missingDates = replacementDays
      .map((day) => day.calendar_date)
      .filter((selectedDate) => !replacementDetailsByDate[selectedDate]);
    if (!missingDates.length) return;
    let active = true;
    void Promise.all(missingDates.map((selectedDate) => apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${selectedDate}`)))
      .then((details) => {
        if (!active) return;
        setReplacementDetailsByDate((current) => ({ ...current, ...Object.fromEntries(details.map((detail) => [detail.calendar_date, detail])) }));
      })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); });
    return () => { active = false; };
  }, [apiRequest, replacementDays, replacementDetailsByDate, status]);

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated") return;
    let active = true;
    const timeout = setTimeout(() => {
      setLoading(true);
      setError(null);
      void apiRequest<LibraryPageData>(`/api/v1/library/daily-plans?limit=50&search=${encodeURIComponent(query)}`)
        .then((page) => { if (active) setPlans(page.items); })
        .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
        .finally(() => { if (active) setLoading(false); });
    }, query ? 220 : 0);
    return () => { active = false; clearTimeout(timeout); };
  }, [apiRequest, query, status]));

  async function assign(days: CalendarDayDetailData[]) {
    if (!selected) return;
    await Promise.all(days.map((day) => apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${day.calendar_date}/plan`, {
        body: JSON.stringify({ dailyplan_id: selected.id, assignment_key: Crypto.randomUUID(), replace_existing: day.has_plan }),
        method: "PUT",
      })));
    router.dismissTo(returnHref as Href);
  }

  async function reviewAssignment() {
    if (!selected || !selectedDateList.length) return;
    setBusy(true);
    setError(null);
    try {
      const currentDays = await Promise.all(selectedDateList.map((selectedDate) => apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${selectedDate}`)));
      setSelectedDaysByDate((current) => ({ ...current, ...Object.fromEntries(currentDays.map((day) => [day.calendar_date, day])) }));
      setMonthOverview((current) => current ? { ...current, days: current.days.map((day) => currentDays.find((fresh) => fresh.calendar_date === day.calendar_date) ?? day) } : current);
      const protectedDays = currentDays.filter((day) => day.has_execution);
      if (protectedDays.length) {
        setError(`${protectedDays.length === 1 ? "La fecha seleccionada tiene" : `${protectedDays.length} fechas seleccionadas tienen`} registros de cumplimiento y no se puede reemplazar su plan.`);
      } else {
        const replacements = currentDays.filter((day) => day.has_plan);
        if (replacements.length) setConfirmReplacement(replacements);
        else await assign(currentDays);
      }
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function confirmAssignments() {
    if (!confirmReplacement) return;
    setBusy(true);
    setError(null);
    try {
      const currentDays = await Promise.all(selectedDateList.map((selectedDate) => apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${selectedDate}`)));
      setSelectedDaysByDate((current) => ({ ...current, ...Object.fromEntries(currentDays.map((day) => [day.calendar_date, day])) }));
      setMonthOverview((current) => current ? { ...current, days: current.days.map((day) => currentDays.find((fresh) => fresh.calendar_date === day.calendar_date) ?? day) } : current);
      if (currentDays.some((day) => day.has_execution)) {
        setConfirmReplacement(null);
        setError("Una de las fechas seleccionadas ahora tiene registros de cumplimiento y ya no se puede reemplazar.");
        return;
      }
      const confirmedDates = new Set(confirmReplacement.map((day) => day.calendar_date));
      const currentReplacements = currentDays.filter((day) => day.has_plan);
      if (currentReplacements.some((day) => !confirmedDates.has(day.calendar_date))) {
        setConfirmReplacement(currentReplacements);
        setError("Cambió la asignación de una fecha. Revisa qué minuta se reemplazará antes de continuar.");
        return;
      }
      await assign(currentDays);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  function toggleDate(day: CalendarDay) {
    if (!localToday || day.calendar_date < localToday || day.has_execution) return;
    setConfirmReplacement(null);
    setError(null);
    if (selectedDates.includes(day.calendar_date)) {
      setSelectedDates((current) => current.filter((value) => value !== day.calendar_date));
      setSelectedDaysByDate((current) => {
        const next = { ...current };
        delete next[day.calendar_date];
        return next;
      });
      setReplacementDetailsByDate((current) => {
        const next = { ...current };
        delete next[day.calendar_date];
        return next;
      });
      return;
    }
    if (selectedDates.length >= 62) {
      setError("Puedes elegir hasta 62 fechas por calendarización.");
      return;
    }
    setSelectedDates((current) => [...current, day.calendar_date]);
    setSelectedDaysByDate((current) => ({ ...current, [day.calendar_date]: day }));
  }

  function changeMonth(delta: number) {
    if (!visibleMonth) return;
    const nextMonth = shiftMonth(visibleMonth, delta);
    const cached = monthCache.get(nextMonth);
    setMonthLoading(!cached);
    setError(null);
    setMonthOverview(cached ?? emptyMonthOverview(nextMonth, localToday));
    setVisibleMonth(nextMonth);
  }

  if (status === "anonymous") return <Redirect href="/login" />;

  if (selected) return <Screen headerMode="preserve">
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    <View style={styles.calendarSection}>
      <Text style={styles.calendarLabel}>Selecciona las fechas para esta minuta:</Text>
      <View style={styles.monthNavigation}>
        <Pressable accessibilityLabel="Mes anterior" accessibilityRole="button" accessibilityState={{ disabled: !visibleMonth || !localToday || visibleMonth <= monthKeyFromDate(localToday) }} disabled={!visibleMonth || !localToday || visibleMonth <= monthKeyFromDate(localToday)} onPress={() => changeMonth(-1)} style={styles.monthArrow}>
          <ChevronLeft color={tokens.color.textMain} size={20} />
        </Pressable>
        <Text accessibilityRole="header" style={styles.monthTitle}>{visibleMonth ? monthLabel(visibleMonth) : ""}</Text>
        <Pressable accessibilityLabel="Mes siguiente" accessibilityRole="button" onPress={() => changeMonth(1)} style={styles.monthArrow}>
          <ChevronRight color={tokens.color.textMain} size={20} />
        </Pressable>
      </View>
      <View style={styles.grid}>
        {(["L", "M", "M", "J", "V", "S", "D"] as const).map((label, index) => <Text key={`weekday-${index}`} style={styles.gridHeader}>{label}</Text>)}
        {monthOverview?.days.map((day) => {
          const isPast = Boolean(localToday && day.calendar_date < localToday);
          const isProtected = day.has_execution;
          const isSelected = selectedDates.includes(day.calendar_date);
          const isFuturePlanDimmed = day.has_plan && day.calendar_date >= localToday && monthKeyFromDate(day.calendar_date) !== visibleMonth;
          const commitmentKinds = commitmentDotKinds(day.commitments);
          return <Pressable
            accessibilityLabel={`${readableDate(day.calendar_date)}: ${isSelected ? "seleccionado" : isPast ? "fecha anterior" : isProtected ? "con cumplimiento registrado" : day.has_plan ? "con minuta asignada" : "sin minuta"}${commitmentKinds.length ? `; ${commitmentKinds.map((kind) => commitmentPresentation[kind].label).join(", ")}` : ""}`}
            accessibilityRole="checkbox"
            accessibilityState={{ checked: isSelected, disabled: monthLoading || isPast || isProtected }}
            disabled={monthLoading || isPast || isProtected}
            key={day.calendar_date}
            onLayout={day.calendar_date === localToday ? ({ nativeEvent: { layout } }) => {
              setTodaySize((current) => current.width === layout.width && current.height === layout.height ? current : { width: layout.width, height: layout.height });
            } : undefined}
            onPress={() => toggleDate(day)}
            style={[styles.gridDate, day.has_plan && styles.gridDateWithPlan, isFuturePlanDimmed && styles.gridDateFuturePlanDimmed, isSelected && styles.gridDateSelected, monthKeyFromDate(day.calendar_date) !== visibleMonth && !day.has_plan && styles.gridDateAdjacent, (isPast || isProtected) && styles.gridDatePast, day.calendar_date === localToday && styles.gridDateToday]}>
            <Text style={[styles.gridNumber, day.has_plan && styles.gridNumberWithPlan, isPast && styles.gridNumberPast, isSelected && styles.gridNumberSelected]}>{day.calendar_date.slice(8, 10)}</Text>
            {commitmentKinds.length ? <View style={[styles.gridCommitmentDots, day.calendar_date === localToday && styles.gridCommitmentDotsToday]}>{commitmentKinds.map((kind) => <View key={kind} style={[styles.gridCommitmentDot, { backgroundColor: commitmentPresentation[kind].color }]} />)}</View> : null}
            {day.calendar_date === localToday ? <CalendarTodayOutline {...todaySize} /> : null}
          </Pressable>;
        })}
      </View>
    </View>
    <View style={styles.calendarAction}>
      {replacementDays.length ? <Text style={styles.replacementCount}>{replacementDays.length === 1 ? "1 minuta será reemplazada" : `${replacementDays.length} minutas serán reemplazadas`}</Text> : null}
      {confirmReplacement ? <ConfirmationState
        busy={busy}
        confirmLabel={confirmReplacement.length === 1 ? "Reemplazar y calendarizar" : `Reemplazar ${confirmReplacement.length} planes`}
        message={`${confirmReplacement.length === 1 ? `“${confirmReplacement[0].plan_name ?? "La minuta actual"}” ya está asignada al ${readableDate(confirmReplacement[0].calendar_date)}.` : `${confirmReplacement.length} fechas ya tienen una minuta asignada.`} ${confirmReplacement.length === 1 ? "Conservará" : "Conservarán"} su historial. “${selected.name}” quedará asignada ${selectedDateList.length === 1 ? `al ${readableDate(selectedDateList[0])}` : `a las ${selectedDateList.length} fechas seleccionadas`}.`}
        onCancel={() => setConfirmReplacement(null)}
        onConfirm={() => void confirmAssignments()}
        title={confirmReplacement.length === 1 ? "¿Reemplazar el plan de esta fecha?" : "¿Reemplazar los planes de estas fechas?"}
      /> : <Button
        disabled={busy || !localToday || !selectedDateList.length}
        icon={<Pin color={tokens.color.surfaceApp} size={18} strokeWidth={2.2} />}
        label={selectedDateList.length <= 1 ? "Calendarizar minuta" : `Calendarizar minuta en ${selectedDateList.length} fechas`}
        loading={busy}
        onPress={() => void reviewAssignment()}
        variant="chipPrimary"
      />}
    </View>
    <DailyPlanPreviewCard eyebrow="Minuta seleccionada" item={selected} />
    {replacementDays.length ? <View style={styles.replacementSection}>
      <SectionHeading detail={`${replacementDays.length} ${replacementDays.length === 1 ? "fecha" : "fechas"}`} title="Planes que serán reemplazados" />
      {replacementDays.map((day) => {
        const detail = replacementDetailsByDate[day.calendar_date];
        const resolvedDay = detail ?? day;
        const snapshot = detail?.plan_snapshot;
        return <NutritionEntityCard
          entity="dailyPlan"
          eyebrow={readableDate(day.calendar_date).toUpperCase()}
          key={day.calendar_date}
          nutrition={calendarDayNutrition(resolvedDay)}
          subtitle={day.source_program_name ?? undefined}
          title={day.plan_name}>
          {snapshot ? <SnapshotMealPanels items={(snapshot.meals ?? []).map((meal, index) => snapshotMealPanelItem(meal, index, snapshot.totals))} nestedScroll showEditTab={false} /> : <LoadingState label="Cargando panel de comidas…" />}
        </NutritionEntityCard>;
      })}
    </View> : null}
  </Screen>;

  if (initialPlanId) return error
    ? <Screen headerMode="preserve"><InlineNotice tone="error">{error}</InlineNotice><Button label="Volver" onPress={() => router.dismissTo(returnHref)} /></Screen>
    : <LoadingState label="Abriendo minuta para calendarizar…" />;

  return <SafeAreaView edges={["left", "right"]} style={styles.selectionSafeArea}>
    <ScrollView
      automaticallyAdjustKeyboardInsets
      contentContainerStyle={styles.selectionScrollContent}
      keyboardDismissMode="on-drag"
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
      stickyHeaderIndices={[0]}>
      <View style={styles.selectionSticky}>
        <PickerEntryTabs createLabel="Crear Nuevo" onCreate={() => router.push({ pathname: "/libraries/create", params: { entity: "dailyPlan" } })} />
        <SearchField accessibilityLabel="Buscar minuta diaria" autoCapitalize="words" bleed busy={loading} onChangeText={setQuery} placeholder="Escribe el nombre de una minuta" value={query} />
      </View>
      <View style={styles.options}>
        <SectionHeading detail={`${plans.length} disponibles`} title="Selecciona una minuta diaria" />
        {plans.map((plan) => <DailyPlanPreviewCard action={{ label: "Seleccionar", onPress: () => { setSelected(plan); setError(null); } }} item={plan} key={plan.id} />)}
        {!loading && !plans.length && !error ? <Text style={styles.emptyText}>No encontramos minutas diarias.</Text> : null}
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        {loading && !plans.length ? <LoadingState label="Buscando tus planes…" /> : null}
      </View>
    </ScrollView>
  </SafeAreaView>;
}

const styles = StyleSheet.create({
  calendarLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  calendarAction: { gap: 20, marginBottom: 36 },
  calendarSection: { gap: tokens.spacing.md, marginBottom: -2 },
  replacementCount: { color: tokens.color.textMuted, fontSize: tokens.type.caption, textAlign: "center" },
  emptyText: { color: tokens.color.textMuted, fontSize: tokens.type.body },
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: tokens.spacing.sm },
  gridCommitmentDots: { bottom: 3, flexDirection: "row", gap: 2, position: "absolute" },
  gridCommitmentDotsToday: { bottom: 6 },
  gridCommitmentDot: { borderRadius: 3, height: 4, width: 4 },
  gridDate: { alignItems: "center", borderColor: "transparent", borderRadius: 10, borderWidth: 2, justifyContent: "center", minHeight: 40, width: "13.5%" },
  gridDateToday: { borderWidth: 0 },
  gridDateAdjacent: { opacity: 0.5 },
  gridDatePast: { opacity: 0.35 },
  gridDateSelected: { backgroundColor: `${tokens.color.dailyPlan}73`, borderColor: tokens.color.dailyPlan },
  gridDateWithPlan: { backgroundColor: `${tokens.color.dailyPlan}59` },
  gridDateFuturePlanDimmed: { backgroundColor: `${tokens.color.dailyPlan}33` },
  gridHeader: { color: tokens.color.textMuted, fontSize: 11, textAlign: "center", width: "13.5%" },
  gridNumber: { color: tokens.color.textMain, fontSize: 14, fontWeight: "500" },
  gridNumberPast: { opacity: 0.8 },
  gridNumberSelected: { color: tokens.color.textMain, fontWeight: "700" },
  gridNumberWithPlan: { color: tokens.color.textMain, fontWeight: "700" },
  monthArrow: { alignItems: "center", height: 36, justifyContent: "center", width: 36 },
  monthNavigation: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  monthTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: "600" },
  options: { gap: tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen },
  replacementSection: { gap: tokens.spacing.lg },
  selectionSafeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  selectionScrollContent: { flexGrow: 1, paddingBottom: 42 },
  selectionSticky: { backgroundColor: tokens.color.surfaceApp, gap: tokens.spacing.xs, paddingBottom: tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen, zIndex: 2 },
});
