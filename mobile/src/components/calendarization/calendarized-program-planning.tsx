import { type Href, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ActiveProgramDay, CalendarizedDayDetail } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { ProgramDaySelector, ProgramWeekTabs } from "@/components/libraries/program-planning-controls";
import { NutritionEntityCard } from "@/components/nutrition";
import { MealPanels } from "@/components/panels";
import { Card, EntityCardAction, InlineNotice, SectionHeading, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { snapshotAllocation, snapshotCalories, snapshotMealPanelItem } from "./presentation-adapters";

function localDate(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function dayLabel(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { weekday: "narrow" }).format(new Date(`${value}T12:00:00`)).toUpperCase();
}

function preferredDay(days: ActiveProgramDay[]): ActiveProgramDay | undefined {
  const today = localDate();
  return days.find((day) => day.calendar_date === today)
    ?? days.find((day) => day.calendar_date > today)
    ?? days.at(-1);
}

export function CalendarizedProgramPlanning({ days }: { days: ActiveProgramDay[] }) {
  const router = useRouter();
  const { apiRequest } = useSession();
  const weeks = useMemo(() => [...new Set(days.map((day) => day.week_number))], [days]);
  const initialDay = preferredDay(days);
  const [activeWeek, setActiveWeek] = useState(initialDay?.week_number ?? weeks[0] ?? 1);
  const [selectedId, setSelectedId] = useState<number | null>(() => {
    if (initialDay?.has_plan) return initialDay.id;
    return days.find((day) => day.week_number === initialDay?.week_number && day.has_plan)?.id ?? null;
  });
  const [detail, setDetail] = useState<CalendarizedDayDetail | null>(null);
  const [loading, setLoading] = useState(selectedId != null);
  const [error, setError] = useState<string | null>(null);

  const weekDays = useMemo(() => days.filter((day) => day.week_number === activeWeek), [activeWeek, days]);

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
  const totals = snapshot?.totals;
  const totalCalories = snapshotCalories(totals);
  const mealItems = (snapshot?.meals ?? []).map((meal, index) => snapshotMealPanelItem(meal, index, totalCalories));

  if (!weeks.length) return null;

  return (
    <View style={styles.section}>
      <ProgramWeekTabs activeWeek={activeWeek} onChange={selectWeek} weeks={weeks} />
      <Card style={styles.weekCard}>
        <SectionHeading
          detail={`${weekDays.filter((day) => day.has_plan).length} asignados`}
          title="Planes diarios esta semana"
        />
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
            <NutritionEntityCard
              actions={(
                <EntityCardAction
                  label="Ir al detalle del plan calendarizado"
                  onPress={() => router.push(`/program/days/${detail.id}` as Href)}
                  role="link">
                  <ChevronRight color={tokens.color.textMuted} size={21} />
                </EntityCardAction>
              )}
              entity="dailyPlan"
              eyebrow={`SEMANA ${activeWeek} · ${dayLabel(detail.calendar_date)}`}
              indicators={[{ icon: "meal", label: "comidas", value: mealItems.length }]}
              kpiVariant="nested"
              nutrition={{
                calories: totalCalories,
                carbs: { allocation: snapshotAllocation(totals, "carbs_g"), grams: totals?.carbs_g ?? 0 },
                fat: { allocation: snapshotAllocation(totals, "fat_g"), grams: totals?.fat_g ?? 0 },
                protein: { allocation: snapshotAllocation(totals, "protein_g"), grams: totals?.protein_g ?? 0, perKilogram: null },
              }}
              subtitle="Plan diario calendarizado"
              title={snapshot.name ?? detail.plan_name ?? "Plan diario"}>
              <MealPanels items={mealItems} />
            </NutritionEntityCard>
          ) : null}
        </ProgramDaySelector>
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  loading: { alignItems: "center", gap: tokens.spacing.sm, justifyContent: "center", minHeight: 120 },
  section: { gap: tokens.spacing.md },
  weekCard: { gap: tokens.spacing.lg, marginHorizontal: -tokens.spacing.screen },
});
