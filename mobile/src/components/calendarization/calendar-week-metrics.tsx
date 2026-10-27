import { useState } from "react";
import { StyleSheet, View } from "react-native";

import type { CalendarDay } from "@/api/calendar-types";
import { WeekMetricPreview, type ProgramMetricDatum, type WeekMetricFilter } from "@/components/libraries/program-child-card";
import { macroCalorieShares } from "@/components/nutrition";
import { EntityPanelTabs, PanelSurface } from "@/components/panels";
import { tokens } from "@/design/tokens";

const tabs: { key: WeekMetricFilter; label: string }[] = [
  { key: "calories", label: "Calorías" },
  { key: "ppk", label: "PPK" },
  { key: "macros", label: "Macros" },
  { key: "allocation", label: "Alloc" },
  { key: "all", label: "Todos" },
];

function metricData(days: CalendarDay[], weightKg: number | null): ProgramMetricDatum[] {
  return days.map((day) => {
    const protein = day.has_plan ? day.plan_protein_grams ?? 0 : 0;
    const carbs = day.has_plan ? day.plan_carbs_grams ?? 0 : 0;
    const fat = day.has_plan ? day.plan_fat_grams ?? 0 : 0;
    return {
      allocation: macroCalorieShares({ proteinGrams: protein, carbsGrams: carbs, fatGrams: fat }),
      calories: day.has_plan ? day.plan_calories ?? 0 : 0,
      protein,
      carbs,
      fat,
      ppk: day.has_plan ? day.plan_protein_per_kilogram ?? (weightKg && weightKg > 0 ? protein / weightKg : null) : null,
    };
  });
}

function weekday(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { weekday: "narrow" }).format(new Date(`${value}T12:00:00`)).toUpperCase();
}

export function CalendarWeekMetrics({ days, weightKg }: { days: CalendarDay[]; weightKg: number | null }) {
  const [activeTab, setActiveTab] = useState<WeekMetricFilter>("calories");
  return <View style={styles.section}>
    <EntityPanelTabs activeTab={activeTab} contentContainerStyle={styles.tabs} onChange={setActiveTab} tabs={tabs} />
    <PanelSurface style={styles.panel}>
      <View style={styles.panelBody}>
        <WeekMetricPreview axisLabels={days.map((day) => weekday(day.calendar_date))} data={metricData(days, weightKg)} days={days.length} filter={activeTab} />
      </View>
    </PanelSurface>
  </View>;
}

const styles = StyleSheet.create({
  section: { gap: 0 },
  tabs: { paddingLeft: 0 },
  panel: { backgroundColor: tokens.color.surfaceCard, marginHorizontal: -6 },
  panelBody: { paddingBottom: tokens.spacing.lg, paddingHorizontal: tokens.layout.reducedInset, paddingTop: tokens.spacing.sm },
});
