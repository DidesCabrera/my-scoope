import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ActiveProgramDay, CalendarizedDayDetail, LibraryFoodPanelItem, LibraryWeekPanelItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { ProgramDaySelector, ProgramWeekHeading, ProgramWeekTabs } from "@/components/libraries/program-planning-controls";
import { FoodPanels, type FoodPanelItem } from "@/components/panels";
import { InlineNotice, SectionDivider, SectionHeading, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { CalendarizedDailyPlanCard } from "./calendarized-daily-plan-card";

function localDate(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function dayLabel(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { weekday: "narrow" }).format(new Date(`${value}T12:00:00`)).toUpperCase();
}

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short" }).format(new Date(`${value}T12:00:00`));
}

function weekDateRange(days: ActiveProgramDay[]): string {
  const dates = days.map((day) => day.calendar_date).sort();
  if (!dates.length) return "Sin fechas";
  return `${dateLabel(dates[0])} — ${dateLabel(dates.at(-1) ?? dates[0])}`;
}

function preferredDay(days: ActiveProgramDay[]): ActiveProgramDay | undefined {
  const today = localDate();
  return days.find((day) => day.calendar_date === today)
    ?? days.find((day) => day.calendar_date > today)
    ?? days.at(-1);
}

function foodPanelItem(item: LibraryFoodPanelItem): FoodPanelItem {
  return {
    id: item.id,
    name: item.name,
    quantity: item.quantity,
    quantityUnit: item.quantity_unit,
    calories: item.calories,
    calorieShare: item.calorie_share,
    proteinGrams: item.protein_grams,
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
  const { apiRequest } = useSession();
  const weeks = useMemo(() => [...new Set(days.map((day) => day.week_number))], [days]);
  const initialDay = preferredDay(days);
  const [activeWeek, setActiveWeek] = useState(initialWeek ?? initialDay?.week_number ?? weeks[0] ?? 1);
  const [selectedId, setSelectedId] = useState<number | null>(() => {
    if (initialDay?.has_plan) return initialDay.id;
    return days.find((day) => day.week_number === initialDay?.week_number && day.has_plan)?.id ?? null;
  });
  const [detail, setDetail] = useState<CalendarizedDayDetail | null>(null);
  const [loading, setLoading] = useState(selectedId != null);
  const [error, setError] = useState<string | null>(null);

  const weekDays = useMemo(() => days.filter((day) => day.week_number === activeWeek), [activeWeek, days]);
  const weekData = weeksData.find((week) => week.week_number === activeWeek);
  const weekFoods = (weekData?.foods ?? []).map(foodPanelItem);

  function selectWeek(week: number) {
    const nextDays = days.filter((day) => day.week_number === week);
    const today = localDate();
    const next = nextDays.find((day) => day.calendar_date === today && day.has_plan)
      ?? nextDays.find((day) => day.has_plan);
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

  const snapshot = detail?.plan_snapshot;

  if (!weeks.length) return null;

  return (
    <View style={styles.section}>
      {showWeekTabs ? <ProgramWeekTabs activeWeek={activeWeek} onChange={selectWeek} weeks={weeks} /> : null}
      <View style={styles.weekContent}>
        <ProgramWeekHeading detail={weekDateRange(weekDays)} week={activeWeek} />
        <ProgramDaySelector
          accessibilityLabel={`Planes diarios de Semana ${activeWeek}`}
          days={weekDays.map((day) => ({ filled: day.has_plan, id: day.id, label: dayLabel(day.calendar_date) }))}
          onSelect={(day) => selectDay(Number(day.id))}
          selectedId={selectedId}>
          {loading ? (
            <View style={styles.loading}>
              <ActivityIndicator color={tokens.color.program} />
              <Text style={textStyles.muted}>Abriendo el plan diario…</Text>
            </View>
          ) : error ? (
            <InlineNotice tone="error">{error}</InlineNotice>
          ) : detail?.has_plan && snapshot ? (
            <CalendarizedDailyPlanCard dayId={detail.id} eyebrow={`SEMANA ${activeWeek} · ${dayLabel(detail.calendar_date)}`} mealExecution={detail.meal_execution} planName={detail.plan_name} snapshot={snapshot} />
          ) : null}
        </ProgramDaySelector>

        <SectionDivider spacing="compact" tone="soft" />
        <SectionHeading detail={`${weekData?.foods_count ?? weekFoods.length} alimentos`} title="Alimentos en esta semana" />
        <FoodPanels items={weekFoods} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  loading: { alignItems: "center", gap: tokens.spacing.sm, justifyContent: "center", minHeight: 120 },
  section: { gap: tokens.spacing.md },
  weekContent: { gap: tokens.spacing.lg, minWidth: 0, paddingTop: tokens.spacing.md, width: "100%" },
});
