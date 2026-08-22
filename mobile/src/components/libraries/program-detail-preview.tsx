import { MoreHorizontal, Plus } from "lucide-react-native";
import type { ReactNode } from "react";
import { useRef, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View, type ScrollViewProps } from "react-native";

import { Card } from "@/components/ui/primitives";
import { FoodPanels, type FoodPanelItem } from "@/components/panels";
import { SectionHeading } from "@/components/ui/typography";
import { tokens } from "@/design/tokens";
import type { LibraryFoodPanelItem, LibraryItem, LibraryWeekPanelItem } from "@/api/types";
import { EntityHeading, EntityIcon, layoutStyles, StructuralIndicators } from "@/components/ui";
import { ProgramMetricPreview, programDailyMetricData } from "./program-child-card";
import { ProgramDailyPlanPreview } from "./program-daily-plan-preview";
import { ProgramDaySelector, ProgramWeekTabs } from "./program-planning-controls";
import { ProgramDayComparisonPanels, type ProgramDayNutrition } from "./program-day-comparison-panels";
import { ProgramWeekComparisonPanels, type ProgramWeekSummary } from "./program-week-comparison-panels";

const weekSummaries: ProgramWeekSummary[] = [
  { allocation: { carbs: 47, fat: 29, protein: 24 }, averageCalories: 2040, calories: 14280, carbsGrams: 1546, dailyPlans: 7, fatGrams: 427, id: "week-1", proteinGrams: 1064, week: 1 },
  { allocation: { carbs: 46, fat: 29, protein: 25 }, averageCalories: 2087, calories: 14610, carbsGrams: 1574, dailyPlans: 7, fatGrams: 438, id: "week-2", proteinGrams: 1108, week: 2 },
];

const dayLabels = ["L", "M", "X", "J", "V", "S", "D"];

const weekFoodItems: FoodPanelItem[] = [
  { calories: 1210, calorieShare: 21, carbsAllocation: 75, carbsGrams: 226, fatAllocation: 12, fatGrams: 16, id: "week-rice", name: "Arroz cocido", proteinAllocation: 13, proteinGrams: 39, quantity: 1260, quantityUnit: "g" },
  { calories: 1848, calorieShare: 32, carbsAllocation: 0, carbsGrams: 0, fatAllocation: 24, fatGrams: 49, id: "week-chicken", name: "Pechuga de pollo", proteinAllocation: 76, proteinGrams: 322, quantity: 1120, quantityUnit: "g" },
  { calories: 842, calorieShare: 15, carbsAllocation: 39, carbsGrams: 82, fatAllocation: 33, fatGrams: 31, id: "week-yogurt", name: "Yogur griego", proteinAllocation: 28, proteinGrams: 59, quantity: 1260, quantityUnit: "g" },
  { calories: 624, calorieShare: 11, carbsAllocation: 92, carbsGrams: 144, fatAllocation: 3, fatGrams: 2, id: "week-banana", name: "Plátano", proteinAllocation: 5, proteinGrams: 8, quantity: 840, quantityUnit: "g" },
];

function CompactAction({ label, onPress, children }: { label: string; onPress(): void; children: ReactNode }) {
  return (
    <Pressable accessibilityLabel={label} accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.compactAction, pressed && styles.pressed]}>
      {children}
    </Pressable>
  );
}

function ProgramDaysGrid({ week, weekData }: { week: number; weekData?: LibraryWeekPanelItem }) {
  const filledDays = weekData ? weekData.days.map((day) => Boolean(day.plan_name)) : week === 1 ? [true, true, true, true, true, false, true] : [true, true, false, true, true, true, true];
  const labels = weekData?.days.map((day) => day.day_label.slice(0, 1).toUpperCase()) ?? dayLabels;
  const [selectedDay, setSelectedDay] = useState<number | null>(() => filledDays[0] ? 0 : null);
  return (
    <ProgramDaySelector
      accessibilityLabel={`Planes diarios de Semana ${week}`}
      days={labels.map((label, index) => ({ filled: filledDays[index], id: index, label }))}
      onSelect={(day) => setSelectedDay(Number(day.id))}
      selectedId={selectedDay}>
      {selectedDay !== null ? <ProgramDailyPlanPreview day={weekData?.days[selectedDay]} dayLabel={labels[selectedDay]} week={week} /> : null}
    </ProgramDaySelector>
  );
}

function dayRows(week: LibraryWeekPanelItem): ProgramDayNutrition[] {
  return week.days.map((day) => ({
    allocation: {
      protein: day.nutrition?.protein.allocation ?? 0,
      carbs: day.nutrition?.carbs.allocation ?? 0,
      fat: day.nutrition?.fat.allocation ?? 0,
    },
    calorieShare: day.nutrition ? day.nutrition.calories / Math.max(week.calories, 1) * 100 : 0,
    calories: day.nutrition?.calories ?? 0,
    carbsGrams: day.nutrition?.carbs.grams ?? 0,
    day: day.day_label,
    fatGrams: day.nutrition?.fat.grams ?? 0,
    id: day.id ?? `${week.id}:day:${day.day_number ?? day.day_label}`,
    planName: day.plan_name,
    ppk: day.nutrition?.protein.per_kilogram ?? 0,
    proteinGrams: day.nutrition?.protein.grams ?? 0,
  }));
}

function foodItem(item: LibraryFoodPanelItem): FoodPanelItem {
  return { id: item.id, name: item.name, quantity: item.quantity, quantityUnit: item.quantity_unit, calories: item.calories, calorieShare: item.calorie_share, proteinGrams: item.protein_grams, carbsGrams: item.carbs_grams, fatGrams: item.fat_grams, proteinAllocation: item.protein_allocation, carbsAllocation: item.carbs_allocation, fatAllocation: item.fat_allocation };
}

function ProgramWeekDetail({ week, weekData }: { week: number; weekData?: LibraryWeekPanelItem }) {
  const liveMetricData = weekData ? programDailyMetricData([weekData]) : undefined;
  return (
    <Card style={styles.weekCard}>
      <View style={styles.weekCardHeader}>
        <View style={styles.weekIdentity}>
          <View style={styles.weekEyebrow}>
            <EntityIcon entity="program" size="compact" />
            <Text style={styles.weekEyebrowText}>SEMANA {week}</Text>
          </View>
          <StructuralIndicators
            entity="program"
            indicators={[
              { icon: "dailyPlan", label: "planes diarios", value: weekData ? weekData.filled_days_count ?? weekData.days.filter((day) => day.plan_name).length : 6 },
              { icon: "meal", label: "comidas", value: weekData?.meals_count ?? 0 },
              { icon: "food", label: "alimentos", value: weekData?.foods_count ?? weekData?.foods?.length ?? 0 },
            ]}
          />
        </View>
        <CompactAction label={`Más acciones para Semana ${week}`} onPress={() => undefined}>
          <MoreHorizontal color={tokens.color.textMuted} size={21} />
        </CompactAction>
      </View>

      <ProgramMetricPreview axisLabels={weekData?.days.map((day) => day.day_label.slice(0, 1).toUpperCase()) ?? dayLabels} data={liveMetricData} days={7} style={layoutStyles.cardContentBleed} />

      <SectionHeading title="Tabla de comparación entre planes diarios" />
      <ProgramDayComparisonPanels key={`comparison-${week}`} rows={weekData ? dayRows(weekData) : undefined} week={week} />

      <View style={styles.sectionDivider} />
      <SectionHeading detail={`${weekData ? weekData.filled_days_count ?? weekData.days.filter((day) => day.plan_name).length : 6} asignados`} title="Planes diarios esta semana" />
      <ProgramDaysGrid key={week} week={week} weekData={weekData} />

      <View style={styles.sectionDivider} />
      <SectionHeading detail={`${weekData?.foods_count ?? weekData?.foods?.length ?? 28} alimentos`} title="Alimentos en esta semana" />
      <FoodPanels items={weekData ? (weekData.foods ?? []).map(foodItem) : weekFoodItems} />
    </Card>
  );
}

type ProgramDetailPreviewProps = {
  footer?: ReactNode;
  item?: LibraryItem;
  onScroll?: ScrollViewProps["onScroll"];
  scrollable?: boolean;
};

export function ProgramDetailPreview({ footer, item, onScroll, scrollable = false }: ProgramDetailPreviewProps = {}) {
  const [activeWeek, setActiveWeek] = useState(1);
  const [weekTabsPinned, setWeekTabsPinned] = useState(false);
  const weekTabsOffset = useRef(Number.POSITIVE_INFINITY);
  const liveWeeks = item?.panel.kind === "weeks" ? item.panel.weeks : [];
  const displayedWeeks = liveWeeks.length ? liveWeeks.map((week) => week.week_number) : [1, 2];
  const liveSummaries: ProgramWeekSummary[] = liveWeeks.map((week) => { const filledDays = week.filled_days_count ?? week.days.filter((day) => day.plan_name).length; return { allocation: { protein: week.protein_allocation, carbs: week.carbs_allocation, fat: week.fat_allocation }, averageCalories: week.average_calories ?? week.calories / Math.max(filledDays, 1), calories: week.calories, carbsGrams: week.carbs_grams, dailyPlans: filledDays, fatGrams: week.fat_grams, id: week.id, proteinGrams: week.protein_grams, week: week.week_number }; });
  const selectedWeek = liveWeeks.find((week) => week.week_number === activeWeek);
  const liveMetrics = liveWeeks.length ? programDailyMetricData(liveWeeks) : undefined;
  const weeksCount = liveWeeks.length || 2;
  const plansCount = liveWeeks.reduce((sum, week) => sum + (week.filled_days_count ?? week.days.filter((day) => day.plan_name).length), 0) || 12;
  const foodsCount = liveWeeks.reduce((maximum, week) => Math.max(maximum, week.foods_count ?? week.foods?.length ?? 0), 0) || 36;

  const overview = (
    <View style={styles.overview}>
        <EntityHeading
          entity="program"
          indicators={[
            { label: "semanas", value: `${weeksCount} SEMANAS` },
            { icon: "dailyPlan", label: "planes asignados", value: plansCount },
            { icon: "food", label: "alimentos", value: foodsCount },
          ]}
          title={item?.name ?? "Programa de recomposición"}
          variant="page"
        />

        <ProgramMetricPreview axisLabels={liveWeeks.map((week) => `S${week.week_number}`)} data={liveMetrics} days={liveMetrics?.length ?? 14} style={layoutStyles.cardContentBleed} />

        <View style={styles.sectionTitleWithAction}>
          <SectionHeading title="Tabla de comparación entre semanas" />
          <Pressable accessibilityRole="button" onPress={() => undefined} style={({ pressed }) => [styles.addWeekButton, pressed && styles.pressed]}>
            <Plus color={tokens.color.surfaceApp} size={17} />
            <Text style={styles.addWeekText}>Agregar semana</Text>
          </Pressable>
        </View>
        <ProgramWeekComparisonPanels weeks={liveSummaries.length ? liveSummaries : weekSummaries} />
    </View>
  );

  const planningHeader = (
    <View style={styles.planningHeader}>
      <View style={styles.planningIdentity}>
        <EntityIcon entity="program" />
        <Text style={styles.planningTitle}>Planificación por semanas</Text>
      </View>
      <StructuralIndicators entity="program" indicators={[{ icon: "week", label: "semanas", value: `${weeksCount} SEMANAS` }]} />
    </View>
  );

  const weekTabs = (
    <View
      onLayout={scrollable ? ({ nativeEvent }) => { weekTabsOffset.current = nativeEvent.layout.y; } : undefined}
      style={scrollable ? [styles.weekTabsSticky, weekTabsPinned && styles.weekTabsStickyPinned] : styles.weekTabsEmbedded}>
      <ProgramWeekTabs activeWeek={activeWeek} onChange={setActiveWeek} weeks={displayedWeeks} />
    </View>
  );

  if (scrollable) {
    return (
      <ScrollView
        contentContainerStyle={styles.screenContent}
        onScroll={(event) => {
          const pinned = event.nativeEvent.contentOffset.y >= weekTabsOffset.current;
          if (pinned !== weekTabsPinned) setWeekTabsPinned(pinned);
          onScroll?.(event);
        }}
        scrollEventThrottle={16}
        stickyHeaderIndices={[3]}
        style={styles.screen}>
        {overview}
        <View style={styles.majorDividerScreen} />
        <View style={styles.planningHeaderScreen}>{planningHeader}</View>
        {weekTabs}
        <ProgramWeekDetail week={activeWeek} weekData={selectedWeek} />
        {footer ? <View style={styles.footer}>{footer}</View> : null}
      </ScrollView>
    );
  }

  return (
    <View style={styles.page}>
      {overview}
      <View style={styles.majorDivider} />
      <View style={styles.planningSection}>
        {planningHeader}
        {weekTabs}
        <ProgramWeekDetail week={activeWeek} weekData={selectedWeek} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  screenContent: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  page: { gap: tokens.spacing.xl, minWidth: 0, width: "100%" },
  overview: { gap: tokens.spacing.lg, minWidth: 0 },
  planningSection: { gap: tokens.spacing.md, minWidth: 0 },
  majorDivider: { backgroundColor: tokens.color.borderDefault, height: 1 },
  majorDividerScreen: { backgroundColor: tokens.color.borderDefault, height: 1, marginVertical: tokens.spacing.xl },
  sectionDivider: { backgroundColor: tokens.color.borderSoft, height: 1, marginVertical: tokens.spacing.xs },
  sectionTitleWithAction: { alignItems: "center", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.md, justifyContent: "space-between" },
  addWeekButton: { alignItems: "center", backgroundColor: tokens.color.textMain, borderRadius: tokens.radius.md, flexDirection: "row", gap: tokens.spacing.xs, minHeight: 38, paddingHorizontal: tokens.spacing.md },
  addWeekText: { color: tokens.color.surfaceApp, fontSize: tokens.type.caption, fontWeight: "700" },
  planningHeader: { alignItems: "center", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.md, justifyContent: "space-between" },
  planningHeaderScreen: { marginBottom: tokens.spacing.md },
  planningIdentity: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  planningTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "700" },
  weekTabsSticky: { backgroundColor: tokens.color.surfaceApp, borderBottomColor: "transparent", borderBottomWidth: 1, marginHorizontal: -tokens.spacing.screen, paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.sm, zIndex: 2 },
  weekTabsStickyPinned: { borderBottomColor: tokens.color.borderDefault },
  weekTabsEmbedded: { paddingBottom: tokens.spacing.sm },
  footer: { gap: tokens.spacing.lg, marginTop: tokens.spacing.xl },
  weekCard: { gap: tokens.spacing.lg, marginHorizontal: -tokens.spacing.screen },
  weekCardHeader: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  weekIdentity: { alignItems: "flex-start", flex: 1, gap: tokens.spacing.sm, minWidth: 0 },
  weekEyebrow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  weekEyebrowText: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: "700" },
  compactAction: { alignItems: "center", height: 34, justifyContent: "center", width: 34 },
  pressed: { opacity: 0.68 },
});
