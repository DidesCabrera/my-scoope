import { type Href, Redirect, Stack, useFocusEffect, useRouter } from "expo-router";
import * as Crypto from "expo-crypto";
import { CalendarClock, Camera, Pin, Scale, Weight } from "lucide-react-native";
import { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ActiveProgramData, CalendarDayDetailData, CalendarProgressData, CalendarizedDayDetail, ComparisonKind, HomeData, MealCheckInInput, TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarizedDailyPlanCard } from "@/components/calendarization/calendarized-daily-plan-card";
import { subscribeToCalendarizedDayUpdates } from "@/components/calendarization/calendarized-day-updates";
import { normalizeMealExecution } from "@/components/calendarization/meal-execution";
import { PinnedDailyPlanCard } from "@/components/calendarization/pinned-daily-plan-card";
import { compactDateLabel } from "@/components/calendarization/current-week";
import { CurrentWeekSection } from "@/components/calendarization/current-week-section";
import { HomeActions } from "@/components/home-actions";
import { ComparisonCreateActions } from "@/components/comparisons";
import { HomeLibraryGrid, type HomeLibraryCounts } from "@/components/home/home-library-grid";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { pickerHref } from "@/components/pickers/composition-picker-screen";
import type { MealPanelEditing, MealPanelItem } from "@/components/panels";
import { Button, Card, Chip, GuideMetric, InlineNotice, LoadingState, MutationStatusModal, Screen, SectionTitle, textStyles, useMutationStatus } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { syncNativeRemindersForProgram } from "@/notifications/native-reminders";

function displayWeight(value: number): string {
  return new Intl.NumberFormat("es-CL", { maximumFractionDigits: 1, minimumFractionDigits: 1 }).format(value);
}

function optimisticMealExecution(data: TodayData, mealKey: string, completed: boolean): TodayData {
  const mealExecution = normalizeMealExecution(data.meal_execution);
  const status = completed ? "completed" : "skipped";
  const existing = mealExecution.find((item) => item.meal_key === mealKey);
  return {
    ...data,
    meal_execution: existing
      ? mealExecution.map((item) => item.meal_key === mealKey ? { ...item, status } : item)
      : [...mealExecution, { last_event_id: null, meal_key: mealKey, note: "", prepared_food_keys: [], recorded_at: null, status }],
  };
}

function HomeSectionTitle({ children, pinned = false }: { children: string; pinned?: boolean }) {
  return <View style={styles.homeSectionHeading}>
    {pinned ? <Pin color={tokens.color.textMain} size={18} strokeWidth={2.2} /> : null}
    <Text accessibilityRole="header" style={styles.homeSectionTitle}>{children}</Text>
  </View>;
}

function ActiveProgramSectionHeader() {
  return (
    <View style={styles.activeProgramSectionHeader}>
      <View style={styles.activeProgramSectionHeading}>
        <CalendarClock color={tokens.color.textMain} size={19} strokeWidth={2.2} />
        <Text accessibilityRole="header" style={styles.activeProgramSectionTitle}>Tu programa en curso</Text>
      </View>
      <Text style={styles.activeProgramSectionSubtitle}>Usa el programa para planificar fechas. El cumplimiento principal se mide en tu calendario.</Text>
    </View>
  );
}

export default function TodayScreen() {
  const router = useRouter();
  const { status, session, profile, apiRequest } = useSession();
  const [today, setToday] = useState<TodayData | null>(null);
  const [activeProgram, setActiveProgram] = useState<ActiveProgramData | null>(null);
  const [calendarProgress, setCalendarProgress] = useState<CalendarProgressData | null>(null);
  const [latestWeightKg, setLatestWeightKg] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [homeActionsVisible, setHomeActionsVisible] = useState(false);
  const [comparisonActionsVisible, setComparisonActionsVisible] = useState(false);
  const [openComparisonAfterHomeActions, setOpenComparisonAfterHomeActions] = useState(false);
  const [creatingTodayPlan, setCreatingTodayPlan] = useState(false);
  const [savingCompletionMealKey, setSavingCompletionMealKey] = useState<string | null>(null);
  const [libraryCounts, setLibraryCounts] = useState<HomeLibraryCounts>({ dailyPlan: 0, food: 0, meal: 0, program: 0 });
  const { clearStatus, runWithStatus, status: mutationStatus } = useMutationStatus();
  const setHeaderPresentation = useHeaderPresentation();
  const openHomeActions = useCallback(() => setHomeActionsVisible(true), []);

  const openComparisonBuilder = useCallback((kind: ComparisonKind) => {
    router.push({ pathname: "/comparator", params: { create: "1", kind } } as Href);
  }, [router]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [home, nextProgress] = await Promise.all([
        apiRequest<HomeData>("/api/v1/home"),
        apiRequest<CalendarProgressData>("/api/v1/calendar/progress").catch(() => null),
      ]);
      const nextToday = home.today;
      setToday(nextToday);
      setActiveProgram(home.active_program);
      setCalendarProgress(nextProgress);
      setLatestWeightKg(home.latest_weight?.weight_kg ?? null);
      setLibraryCounts({
        dailyPlan: home.library_counts.daily_plan,
        food: home.library_counts.food,
        meal: home.library_counts.meal,
        program: home.library_counts.program,
      });
      if (nextToday.reminders) {
        void syncNativeRemindersForProgram(
          nextToday.reminders,
          nextToday.calendarization?.status ?? null,
          apiRequest,
        ).catch(() => undefined);
      }
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  useEffect(() => subscribeToCalendarizedDayUpdates((day) => {
    setToday((current) => current?.day_id === day.id ? {
      ...current,
      has_plan: day.has_plan,
      meal_execution: day.meal_execution,
      plan_snapshot: day.plan_snapshot,
    } : current);
  }), []);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ action: { label: "Acciones de inicio", onPress: openHomeActions }, mode: "default" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [openHomeActions, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (status === "authenticated" && profile?.review_disclosure_required) return <Redirect href="./disclosures" />;
  if (status === "authenticated" && !profile?.onboarding_completed) return <Redirect href="/onboarding" />;
  if (loading && !today) return <><Stack.Screen options={{ animation: "none", headerShown: false }} /><LoadingState headerVisible={false} /></>;

  const snapshot = today?.plan_snapshot;
  const todayDayId = today?.day_id;
  const firstName = session?.display_name.split(" ")[0] || session?.username || "Atleta";
  const currentWeightKg = latestWeightKg ?? profile?.current_weight_kg ?? today?.measurements?.latest_weight_kg;
  const planContext = today?.calendarization
    ? { color: tokens.color.program, label: "Programa en curso" }
    : today?.day_id
      ? { color: tokens.color.dailyPlan, label: "Plan del calendario" }
    : today?.pinned_plan
      ? { color: tokens.color.dailyPlan, label: "Plan calendarizado" }
      : null;

  async function createTodayPlan() {
    if (!today) return;
    setCreatingTodayPlan(true);
    setError(null);
    try {
      await apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${today.local_date}/plan/draft`, {
        body: JSON.stringify({ assignment_key: Crypto.randomUUID() }),
        method: "POST",
      });
      await load();
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setCreatingTodayPlan(false);
    }
  }

  async function toggleTodayMealCompletion(mealKey: string, completed: boolean, mode: "calendarized" | "pinned") {
    if (savingCompletionMealKey || (mode === "calendarized" && todayDayId == null)) return;
    const previousToday = today;
    setSavingCompletionMealKey(mealKey);
    setError(null);
    if (today) setToday(optimisticMealExecution(today, mealKey, completed));
    try {
      const payload: MealCheckInInput = {
        action: completed ? "completed" : "skipped",
        idempotency_key: Crypto.randomUUID(),
      };
      const path = mode === "pinned"
        ? `/api/v1/today/pinned-plan/meals/${encodeURIComponent(mealKey)}/check-ins`
        : `/api/v1/days/${todayDayId}/meals/${encodeURIComponent(mealKey)}/check-ins`;
      setToday(await apiRequest<TodayData>(path, { body: JSON.stringify(payload), method: "POST" }));
      if (mode === "calendarized") void apiRequest<CalendarProgressData>("/api/v1/calendar/progress")
        .then(setCalendarProgress).catch(() => undefined);
    } catch (nextError) {
      setToday(previousToday);
      setError(userFacingError(nextError));
    } finally {
      setSavingCompletionMealKey(null);
    }
  }

  const calendarizedMealEditing: MealPanelEditing | undefined = todayDayId != null ? {
    onChangeTime: (meal) => router.push({ pathname: "/program/days/[id]/meals/[mealKey]", params: { id: String(todayDayId), mealKey: meal.id } } as Href),
    onDelete: async (meal) => {
      await apiRequest(`/api/v1/program/days/${todayDayId}/meals/${encodeURIComponent(meal.id)}`, { method: "DELETE" });
      await load();
    },
    onOpen: (meal) => router.push({ pathname: "/program/days/[id]/meals/[mealKey]", params: { id: String(todayDayId), mealKey: meal.id } } as Href),
    onToggleCompleted: (meal, completed) => { void toggleTodayMealCompletion(meal.id, completed, "calendarized"); },
    onReorder: async (meals: MealPanelItem[]) => {
      await runWithStatus(async () => {
        const updated = await apiRequest<CalendarizedDayDetail>(`/api/v1/program/days/${todayDayId}/meals/order`, { body: JSON.stringify({ ordered_keys: meals.map((meal) => meal.id) }), method: "PUT" });
        setToday((current) => current?.day_id === updated.id ? {
          ...current,
          meal_execution: updated.meal_execution,
          plan_snapshot: updated.plan_snapshot,
        } : current);
      }, { loadingLabel: "Actualizando plan", successLabel: "Plan actualizado" });
    },
    onReplace: (meal) => router.push(pickerHref("meal-to-calendarized-day", { dayId: todayDayId, relationKey: meal.id })),
  } : undefined;
  const pinnedPlan = today?.pinned_plan;
  const pinnedMealEditing: MealPanelEditing | undefined = pinnedPlan ? {
    onChangeTime: (meal) => {
      if (meal.detailId == null || meal.relationId == null) return;
      router.push({ pathname: "/libraries/meals/[id]", params: { dailyPlanId: String(pinnedPlan.id), dailyPlanMealId: String(meal.relationId), id: String(meal.detailId), mealKey: meal.id, mealTime: meal.time ?? "", pinned: "1" } } as Href);
    },
    onDelete: async (meal) => {
      if (meal.relationId == null) return;
      await apiRequest(`/api/v1/library/daily-plans/${pinnedPlan.id}/meals/${meal.relationId}`, { method: "DELETE" });
      await load();
    },
    onOpen: (meal) => {
      if (meal.detailId == null || meal.relationId == null) return;
      router.push({ pathname: "/libraries/meals/[id]", params: { dailyPlanId: String(pinnedPlan.id), dailyPlanMealId: String(meal.relationId), id: String(meal.detailId), mealKey: meal.id, mealTime: meal.time ?? "", pinned: "1" } } as Href);
    },
    onToggleCompleted: (meal, completed) => { void toggleTodayMealCompletion(meal.id, completed, "pinned"); },
    onReorder: async (meals: MealPanelItem[]) => {
      await runWithStatus(async () => {
        await apiRequest(`/api/v1/library/daily-plans/${pinnedPlan.id}/meals/order`, { body: JSON.stringify({ ordered_ids: meals.map((meal) => meal.relationId) }), method: "PUT" });
        const positions = new Map(meals.map((meal, index) => [meal.id, index]));
        setToday((current) => current?.pinned_plan?.id === pinnedPlan.id ? {
          ...current,
          pinned_plan: {
            ...current.pinned_plan,
            panel: {
              ...current.pinned_plan.panel,
              meals: [...current.pinned_plan.panel.meals].sort((left, right) => (positions.get(left.id) ?? 0) - (positions.get(right.id) ?? 0)),
            },
          },
        } : current);
      }, { loadingLabel: "Actualizando plan", successLabel: "Plan actualizado" });
    },
    onReplace: (meal) => { if (meal.relationId != null) router.push(pickerHref("meal-to-dailyplan", { dailyPlanId: pinnedPlan.id, dailyPlanMealId: meal.relationId })); },
  } : undefined;

  return (
    <>
      <Stack.Screen options={{ headerShown: true }} />
      <Screen headerMode="preserve">
      {today ? <View style={styles.weekRow}><CurrentWeekSection localDate={today.local_date} /></View> : null}
      <View style={styles.greetingRow}>
        <View style={styles.greetingHeading}>
          <Text style={styles.greetingTitle}>{`💪🏻Vamos ${firstName}!`}</Text>
          {currentWeightKg != null ? <GuideMetric onPress={() => router.push("/weight" as Href)} tone="ppk" value={`${displayWeight(currentWeightKg)} kg`} /> : null}
        </View>
        {planContext ? <View style={styles.planContext}><Chip backgroundColor={`${planContext.color}4D`} borderColor={planContext.color} label={planContext.label} textColor={tokens.color.textMain} /></View> : null}
      </View>
      {today?.day_id != null ? <HomeSectionTitle pinned>Tu plan de alimentación para hoy</HomeSectionTitle> : null}

      {today?.day_id != null && today.has_plan && snapshot ? (
        <CalendarizedDailyPlanCard
          apiRequest={apiRequest}
          dayId={todayDayId ?? null}
          dateLabel={compactDateLabel(today.local_date)}
          editing={calendarizedMealEditing}
          eyebrow="PLAN DEL DÍA"
          mealExecution={today.meal_execution}
          onChangeMealTime={async (meal, hour) => {
            await apiRequest(`/api/v1/program/days/${todayDayId}/meals/${encodeURIComponent(meal.id)}`, { body: JSON.stringify({ hour }), headers: { "Content-Type": "application/json" }, method: "PATCH" });
            await load();
          }}
          onAddMeal={todayDayId != null ? () => router.push(pickerHref("meal-to-calendarized-day", { dayId: todayDayId })) : undefined}
          onChanged={load}
          snapshot={snapshot}
        />
      ) : today?.calendarization ? (
        <Card muted>
          <SectionTitle title="Día sin plan" />
          <Text style={textStyles.muted}>Tu calendarización no tiene un plan nutricional previsto para esta fecha.</Text>
        </Card>
      ) : today?.pinned_plan ? (
        <>
          <HomeSectionTitle pinned>Tu plan de alimentación para hoy</HomeSectionTitle>
          <PinnedDailyPlanCard apiRequest={apiRequest} editing={pinnedMealEditing} item={today.pinned_plan} mealExecution={today.meal_execution} onChanged={load} onChangeMealTime={async (meal, hour) => {
            if (meal.relationId == null) return;
            await apiRequest(`/api/v1/library/daily-plans/${pinnedPlan!.id}/meals/${meal.relationId}`, { body: JSON.stringify({ hour }), headers: { "Content-Type": "application/json" }, method: "PATCH" });
            await load();
          }} />
        </>
      ) : today ? (
        <>
          <HomeSectionTitle>Registra tus comidas en un nuevo Plan</HomeSectionTitle>
          <Card accent={tokens.color.dailyPlan}>
            <Button label="Crear un plan para hoy" loading={creatingTodayPlan} onPress={() => void createTodayPlan()} />
            <Button label="Elegir desde Mis Planes Diarios" onPress={() => router.push("/libraries/daily-plans" as Href)} variant="secondary" />
          </Card>
        </>
      ) : null}

      {calendarProgress ? <Card accent={tokens.color.dailyPlan}>
        <SectionTitle detail={calendarProgress.elapsed_meals ? `${calendarProgress.adherence_percent}%` : "Sin registros"} title="Cumplimiento del calendario" />
        <Text style={textStyles.muted}>{calendarProgress.elapsed_meals ? `${calendarProgress.completed_meals} de ${calendarProgress.elapsed_meals} comidas transcurridas` : "Aún no hay comidas transcurridas"} desde {compactDateLabel(calendarProgress.period_start)}.</Text>
        <Button label="Ver calendario" onPress={() => router.push("/calendar" as Href)} variant="secondary" />
      </Card> : null}

      {activeProgram?.calendarization ? (
        <>
          <ActiveProgramSectionHeader />
          <Card accent={tokens.color.program}>
            <SectionTitle title={activeProgram.calendarization.program_name} />
            <Button label="Ver programa en curso" onPress={() => router.push("/program" as Href)} variant="secondary" />
          </Card>
        </>
      ) : null}

      <HomeLibraryGrid counts={libraryCounts} />

      {error ? (
        <>
          <InlineNotice tone="error">{error}</InlineNotice>
          <Button label="Reintentar" loading={loading} onPress={() => void load()} variant="secondary" />
        </>
      ) : null}

      {today?.measurements?.latest_weight_kg != null ? (
        <Card muted>
          <SectionTitle detail={`${today.measurements.count} mediciones`} title="Tendencia del programa" />
          <View style={styles.measurementRow}>
            <Text style={styles.measurementValue}>{displayWeight(today.measurements.latest_weight_kg)} kg</Text>
            {today.measurements.change_kg != null ? (
              <Chip
                borderColor={tokens.color.protein}
                label={`${today.measurements.change_kg > 0 ? "+" : ""}${today.measurements.change_kg.toFixed(1)} kg`}
              />
            ) : null}
          </View>
        </Card>
      ) : null}

      {today?.pending_revision ? (
        <Card accent={tokens.color.warning}>
          <SectionTitle detail={`Desde ${today.pending_revision.effective_from}`} title="Ajuste para revisar" />
          <Text style={textStyles.muted}>{today.pending_revision.rationale}</Text>
          <Button label="Revisar antes de aplicar" onPress={() => router.push("./revision")} />
        </Card>
      ) : null}

      <View style={styles.homeQuickActions}>
        <HomeSectionTitle>Accesos rápidos</HomeSectionTitle>
        <View style={styles.homeFooterActions}>
          <Button icon={<Camera color={tokens.color.textMain} size={20} strokeWidth={2} />} label="Digitalizar etiqueta" onPress={() => router.push("/label-capture" as Href)} variant="secondary" />
          <Button icon={<Weight color={tokens.color.textMain} size={20} strokeWidth={2} />} label="Registrar peso corporal" onPress={() => router.push("/weight" as Href)} variant="secondary" />
          <Button icon={<Scale color={tokens.color.textMain} size={20} strokeWidth={2} />} label="Comparar" onPress={() => setComparisonActionsVisible(true)} variant="secondary" />
        </View>
      </View>

      </Screen>
      <HomeActions
        onCaptureLabel={() => router.push("/label-capture")}
        onClose={() => setHomeActionsVisible(false)}
        onCompare={() => {
          setOpenComparisonAfterHomeActions(true);
          setHomeActionsVisible(false);
        }}
        onDismiss={() => {
          if (!openComparisonAfterHomeActions) return;
          setOpenComparisonAfterHomeActions(false);
          setComparisonActionsVisible(true);
        }}
        onRegisterWeight={() => router.push("/weight")}
        visible={homeActionsVisible}
      />
      <ComparisonCreateActions onClose={() => setComparisonActionsVisible(false)} onSelect={openComparisonBuilder} visible={comparisonActionsVisible} />
      <MutationStatusModal onFinished={clearStatus} status={mutationStatus} />
    </>
  );
}

const styles = StyleSheet.create({
  activeProgramSectionHeader: { gap: tokens.spacing.sm, marginTop: tokens.spacing.xxl },
  activeProgramSectionHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  activeProgramSectionSubtitle: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  activeProgramSectionTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: tokens.weight.extraBold },
  homeSectionHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, marginTop: tokens.spacing.sm },
  homeSectionTitle: { color: tokens.color.textMain, flex: 1, fontSize: 18, fontWeight: tokens.weight.semibold, marginBottom: 0 },
  homeFooterActions: { gap: tokens.spacing.sm, marginTop: tokens.spacing.sm },
  homeQuickActions: { marginTop: tokens.spacing.xl },
  greetingRow: { gap: 0, marginBottom: 0 },
  greetingHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  greetingTitle: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.title, fontWeight: tokens.weight.extraBold, letterSpacing: -0.5 },
  planContext: { alignSelf: "flex-start", marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, marginTop: tokens.spacing.sm },
  weekRow: { marginBottom: tokens.spacing.sm },
  measurementRow: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  measurementValue: { color: tokens.color.textMain, fontSize: 28, fontWeight: "900", fontVariant: ["tabular-nums"] },
});
