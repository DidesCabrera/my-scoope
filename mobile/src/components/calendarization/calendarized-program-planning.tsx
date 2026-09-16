import { useEffect, useMemo, useState } from "react";
import { type Href, useRouter } from "expo-router";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ActiveProgramDay, CalendarizedDayDetail, LibraryFoodPanelItem, LibraryWeekPanelItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { ProgramDaySelector, ProgramWeekHeading, ProgramWeekTabs } from "@/components/libraries/program-planning-controls";
import { pickerHref } from "@/components/pickers/composition-picker-screen";
import { FoodPanels, type FoodPanelItem, type MealPanelEditing, type MealPanelItem } from "@/components/panels";
import { Button, InlineNotice, MutationStatusModal, SectionDivider, SectionHeading, textStyles, useMutationStatus } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { CalendarizedDailyPlanCard } from "./calendarized-daily-plan-card";
import { compactDateLabel, compactMonthLabel, preferredCalendarizedDay } from "./current-week";

function localDate(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function dayLabel(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { weekday: "narrow" }).format(new Date(`${value}T12:00:00`)).toUpperCase();
}

function weekDateRange(days: ActiveProgramDay[]): string {
  const dates = days.map((day) => day.calendar_date).sort();
  if (!dates.length) return "Sin fechas";
  return `${compactDateLabel(dates[0])} — ${compactDateLabel(dates.at(-1) ?? dates[0])}`;
}

function preferredWeek(days: ActiveProgramDay[]): ActiveProgramDay | undefined {
  const today = localDate();
  return days.find((day) => day.calendar_date === today)
    ?? days.find((day) => day.calendar_date > today)
    ?? days.at(-1);
}

function foodPanelItem(item: LibraryFoodPanelItem): FoodPanelItem {
  return {
    detailId: item.detail_id,
    id: item.id,
    name: item.name,
    quantity: item.quantity,
    quantityUnit: item.quantity_unit,
    calories: item.calories,
    calorieShare: item.calorie_share,
    proteinGrams: item.protein_grams,
    proteinPerKilogram: item.protein_per_kilogram,
    carbsGrams: item.carbs_grams,
    fatGrams: item.fat_grams,
    proteinAllocation: item.protein_allocation,
    carbsAllocation: item.carbs_allocation,
    fatAllocation: item.fat_allocation,
  };
}

export function CalendarizedProgramPlanning({
  days,
  initialWeek,
  showWeekTabs = true,
  weeksData = [],
}: {
  days: ActiveProgramDay[];
  initialWeek?: number;
  showWeekTabs?: boolean;
  weeksData?: LibraryWeekPanelItem[];
}) {
  const router = useRouter();
  const { apiRequest } = useSession();
  const weeks = useMemo(() => [...new Set(days.map((day) => day.week_number))], [days]);
  const initialDay = preferredWeek(days);
  const [activeWeek, setActiveWeek] = useState(initialWeek ?? initialDay?.week_number ?? weeks[0] ?? 1);
  const [selectedId, setSelectedId] = useState<number | null>(() => (
    preferredCalendarizedDay(days, initialWeek ?? initialDay?.week_number ?? weeks[0] ?? 1, localDate())?.id ?? null
  ));
  const [detail, setDetail] = useState<CalendarizedDayDetail | null>(null);
  const [loading, setLoading] = useState(selectedId != null);
  const [error, setError] = useState<string | null>(null);
  const { clearStatus, runWithStatus, status: mutationStatus } = useMutationStatus();

  const weekDays = useMemo(
    () => days.filter((day) => day.week_number === activeWeek).sort((left, right) => left.calendar_date.localeCompare(right.calendar_date)),
    [activeWeek, days],
  );
  const weekData = weeksData.find((week) => week.week_number === activeWeek);
  const weekFoods = (weekData?.foods ?? []).map(foodPanelItem);

  function selectWeek(week: number) {
    const next = preferredCalendarizedDay(days, week, localDate());
    setActiveWeek(week);
    setSelectedId(next?.id ?? null);
    setDetail(null);
    setError(null);
    setLoading(Boolean(next));
  }

  function selectDay(id: number) {
    setSelectedId(id);
    setDetail(null);
    setError(null);
    setLoading(true);
  }

  useEffect(() => {
    let active = true;
    if (selectedId == null) return () => { active = false; };
    void apiRequest<CalendarizedDayDetail>(`/api/v1/program/days/${selectedId}`)
      .then((nextDetail) => { if (active) setDetail(nextDetail); })
      .catch((nextError) => { if (active) { setDetail(null); setError(userFacingError(nextError)); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [apiRequest, selectedId]);

  async function mutateSelectedDay(path: string, init: RequestInit) {
    if (selectedId == null) return;
    try {
      await apiRequest(path, init);
      setDetail(await apiRequest<CalendarizedDayDetail>(`/api/v1/program/days/${selectedId}`));
    } catch (nextError) {
      setError(userFacingError(nextError));
      throw nextError;
    }
  }

  const mealEditing: MealPanelEditing | undefined = detail?.has_plan ? {
    onChangeTime: (meal) => router.push({ pathname: "/program/days/[id]/meals/[mealKey]", params: { id: String(detail.id), mealKey: meal.id } } as Href),
    onDelete: async (meal) => mutateSelectedDay(`/api/v1/program/days/${detail.id}/meals/${encodeURIComponent(meal.id)}`, { method: "DELETE" }),
    onOpen: (meal) => router.push({ pathname: "/program/days/[id]/meals/[mealKey]", params: { id: String(detail.id), mealKey: meal.id } } as Href),
    onReorder: async (meals: MealPanelItem[]) => runWithStatus(
      () => mutateSelectedDay(`/api/v1/program/days/${detail.id}/meals/order`, { body: JSON.stringify({ ordered_keys: meals.map((meal) => meal.id) }), method: "PUT" }),
      { loadingLabel: "Actualizando plan", successLabel: "Plan actualizado" },
    ),
    onReplace: (meal) => router.push(pickerHref("meal-to-calendarized-day", { dayId: detail.id, relationKey: meal.id })),
  } : undefined;

  const snapshot = detail?.plan_snapshot;

  if (!weeks.length) return null;

  return (
    <View style={styles.section}>
      {showWeekTabs ? <ProgramWeekTabs activeWeek={activeWeek} onChange={selectWeek} weeks={weeks} /> : null}
      <View style={styles.weekContent}>
        <ProgramWeekHeading detail={weekDateRange(weekDays)} week={activeWeek} />
        <ProgramDaySelector
          accessibilityLabel={`Planes diarios de Semana ${activeWeek}`}
          allowEmptySelection
          days={weekDays.map((day) => ({
            dayOfMonth: Number(day.calendar_date.slice(8, 10)),
            disabled: !day.has_plan && day.calendar_date <= localDate(),
            filled: day.has_plan,
            id: day.id,
            isToday: day.calendar_date === localDate(),
            label: dayLabel(day.calendar_date),
            monthLabel: compactMonthLabel(day.calendar_date),
          }))}
          onSelect={(day) => day.filled
            ? selectDay(Number(day.id))
            : router.push(pickerHref("dailyplan-to-calendarized-day", { dayId: day.id }))}
          selectedId={selectedId}>
          {loading ? (
            <View style={styles.loading}>
              <ActivityIndicator color={tokens.color.program} />
              <Text style={textStyles.muted}>Abriendo el plan diario…</Text>
            </View>
          ) : error ? (
            <InlineNotice tone="error">{error}</InlineNotice>
          ) : detail?.has_plan && snapshot ? (
            <View style={styles.selectedPlan}>
              <CalendarizedDailyPlanCard dayId={detail.id} dateLabel={compactDateLabel(detail.calendar_date)} editing={mealEditing} eyebrow={`SEMANA ${activeWeek} · ${dayLabel(detail.calendar_date)}`} mealExecution={detail.meal_execution} onChangeMealTime={(meal, hour) => mutateSelectedDay(`/api/v1/program/days/${detail.id}/meals/${encodeURIComponent(meal.id)}`, { body: JSON.stringify({ hour }), headers: { "Content-Type": "application/json" }, method: "PATCH" })} planName={detail.plan_name} snapshot={snapshot} />
              {detail.calendar_date > localDate() ? (
                <Button
                  label="Cambiar plan diario"
                  onPress={() => router.push(pickerHref("dailyplan-to-calendarized-day", { dayId: detail.id }))}
                  variant="secondary"
                />
              ) : null}
            </View>
          ) : detail ? (
            <View style={styles.emptyDay}>
              <InlineNotice>Día sin plan. No hay un plan diario asignado para esta fecha.</InlineNotice>
              {detail.calendar_date > localDate() ? (
                <Button
                  label="Agregar plan diario"
                  onPress={() => router.push(pickerHref("dailyplan-to-calendarized-day", { dayId: detail.id }))}
                  variant="secondary"
                />
              ) : null}
            </View>
          ) : null}
        </ProgramDaySelector>

        <SectionDivider spacing="compact" tone="soft" />
        <SectionHeading detail={`${weekData?.foods_count ?? weekFoods.length} alimentos`} title="Alimentos en esta semana" />
        <FoodPanels items={weekFoods} onOpenItem={(food) => { if (food.detailId != null) router.push(`/libraries/foods/${food.detailId}` as Href); }} />
      </View>
      <MutationStatusModal onFinished={clearStatus} status={mutationStatus} />
    </View>
  );
}

const styles = StyleSheet.create({
  loading: { alignItems: "center", gap: tokens.spacing.sm, justifyContent: "center", minHeight: 120 },
  emptyDay: { gap: tokens.spacing.md },
  section: { gap: tokens.spacing.md },
  selectedPlan: { gap: tokens.spacing.md },
  weekContent: { gap: tokens.spacing.lg, minWidth: 0, paddingTop: tokens.spacing.md, width: "100%" },
});
