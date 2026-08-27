import { Copy, MoreHorizontal, Trash2 } from "lucide-react-native";
import type { ReactNode } from "react";
import { useState } from "react";
import { Pressable, ScrollView, StyleSheet, View, type ScrollViewProps } from "react-native";

import { FoodPanels, type FoodPanelItem } from "@/components/panels";
import { SectionHeading } from "@/components/ui/typography";
import { tokens } from "@/design/tokens";
import type { LibraryFoodPanelItem, LibraryItem, LibraryWeekPanelItem } from "@/api/types";
import { EntityHeading, layoutStyles, SectionDivider, StructuralIndicators } from "@/components/ui";
import { Button } from "@/components/ui/controls";
import { ProgramMetricPreview, programDailyMetricData } from "./program-child-card";
import { ProgramDailyPlanPreview } from "./program-daily-plan-preview";
import { ProgramDaySelector, ProgramWeekHeading, ProgramWeekTabs } from "./program-planning-controls";
import { ProgramDayComparisonPanels, type ProgramDayNutrition } from "./program-day-comparison-panels";
import { ProgramWeekComparisonPanels, type ProgramWeekSummary } from "./program-week-comparison-panels";
import { ContextCardActions, type ContextCardAction } from "./context-card-actions";

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

function ProgramDaysGrid({ onAssignDailyPlan, onRemoveDailyPlan, week, weekData }: { onAssignDailyPlan?: (week: number, day: number) => void; onRemoveDailyPlan?: (week: number, day: number) => Promise<void>; week: number; weekData?: LibraryWeekPanelItem }) {
  const filledDays = weekData ? weekData.days.map((day) => Boolean(day.plan_name)) : week === 1 ? [true, true, true, true, true, false, true] : [true, true, false, true, true, true, true];
  const labels = weekData?.days.map((day) => day.day_label.slice(0, 1).toUpperCase()) ?? dayLabels;
  const [selectedDay, setSelectedDay] = useState<number | null>(() => filledDays[0] ? 0 : null);
  return (
    <ProgramDaySelector
      accessibilityLabel={`Planes diarios de Semana ${week}`}
      allowEmptySelection={Boolean(onAssignDailyPlan)}
      days={labels.map((label, index) => ({ filled: filledDays[index], id: index, label }))}
      onSelect={(day) => {
        const index = Number(day.id);
        if (!day.filled && onAssignDailyPlan) {
          onAssignDailyPlan(week, index + 1);
          return;
        }
        setSelectedDay(index);
      }}
      selectedId={selectedDay}>
      {selectedDay !== null ? <ProgramDailyPlanPreview
        day={weekData?.days[selectedDay]}
        dayLabel={labels[selectedDay]}
        onRemove={onRemoveDailyPlan ? () => onRemoveDailyPlan(week, selectedDay + 1) : undefined}
        onReplace={onAssignDailyPlan ? () => onAssignDailyPlan(week, selectedDay + 1) : undefined}
        week={week}
      /> : null}
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
    dayNumber: day.day_number ?? 1,
    fatGrams: day.nutrition?.fat.grams ?? 0,
    id: day.id ?? `${week.id}:day:${day.day_number ?? day.day_label}`,
    planName: day.plan_name,
    ppk: day.nutrition?.protein.per_kilogram ?? 0,
    proteinGrams: day.nutrition?.protein.grams ?? 0,
    week: week.week_number,
  }));
}

function foodItem(item: LibraryFoodPanelItem): FoodPanelItem {
  return { id: item.id, name: item.name, quantity: item.quantity, quantityUnit: item.quantity_unit, calories: item.calories, calorieShare: item.calorie_share, proteinGrams: item.protein_grams, carbsGrams: item.carbs_grams, fatGrams: item.fat_grams, proteinAllocation: item.protein_allocation, carbsAllocation: item.carbs_allocation, fatAllocation: item.fat_allocation };
}

export function ProgramWeekDetail({ canRemoveWeek = false, onAssignDailyPlan, onDuplicateWeek, onRemoveDailyPlan, onRemoveWeek, showHeading = true, week, weekData }: { canRemoveWeek?: boolean; onAssignDailyPlan?: (week: number, day: number) => void; onDuplicateWeek?: (week: number) => Promise<void>; onRemoveDailyPlan?: (week: number, day: number) => Promise<void>; onRemoveWeek?: (week: number) => Promise<void>; showHeading?: boolean; week: number; weekData?: LibraryWeekPanelItem }) {
  const liveMetricData = weekData ? programDailyMetricData([weekData]) : undefined;
  const filledDaysCount = weekData ? weekData.filled_days_count ?? weekData.days.filter((day) => day.plan_name).length : 6;
  const hasPlans = filledDaysCount > 0;
  const weekActions: ContextCardAction[] = [
    ...(onDuplicateWeek ? [{ icon: Copy, key: "duplicate", label: "Duplicar semana", onPress: () => onDuplicateWeek(week) }] : []),
    ...(canRemoveWeek && onRemoveWeek ? [{
      confirmation: {
        confirmLabel: "Eliminar semana",
        message: `Se eliminará la Semana ${week} y sus asignaciones dentro de este programa.`,
        title: `¿Eliminar Semana ${week}?`,
      },
      destructive: true,
      icon: Trash2,
      key: "remove",
      label: "Eliminar semana",
      onPress: () => onRemoveWeek(week),
    }] : []),
  ];
  return (
    <View style={styles.weekContent}>
      {showHeading ? <View style={styles.weekCardHeader}>
        <View style={styles.weekIdentity}>
          <ProgramWeekHeading week={week} />
          {hasPlans ? <StructuralIndicators
            entity="program"
            indicators={[
              { icon: "dailyPlan", label: "planes diarios", value: filledDaysCount },
              { icon: "meal", label: "comidas", value: weekData?.meals_count ?? 0 },
              { icon: "food", label: "alimentos", value: weekData?.foods_count ?? weekData?.foods?.length ?? 0 },
            ]}
          /> : null}
        </View>
        <ContextCardActions
          actions={weekActions}
          label={`Más acciones para Semana ${week}`}
          renderTrigger={(open) => <CompactAction label={`Más acciones para Semana ${week}`} onPress={open}><MoreHorizontal color={tokens.color.textMuted} size={21} /></CompactAction>}
          title={`Semana ${week}`}
        />
      </View> : null}

      {hasPlans ? <>
        <ProgramMetricPreview axisLabels={weekData?.days.map((day) => day.day_label.slice(0, 1).toUpperCase()) ?? dayLabels} axisLeadingLabel="Semana" data={liveMetricData} days={7} style={layoutStyles.cardContentBleed} />

        <SectionHeading title="Tabla de comparación entre planes diarios" />
        <ProgramDayComparisonPanels key={`comparison-${week}`} onAssign={onAssignDailyPlan} onDelete={onRemoveDailyPlan} rows={weekData ? dayRows(weekData) : undefined} week={week} />

        <SectionDivider spacing="compact" tone="soft" />
        <SectionHeading detail={`${filledDaysCount} asignados`} title="Planes diarios esta semana" />
      </> : null}
      <ProgramDaysGrid key={`${week}:${weekData?.days.map((day) => Number(Boolean(day.plan_name))).join("") ?? "demo"}`} onAssignDailyPlan={onAssignDailyPlan} onRemoveDailyPlan={onRemoveDailyPlan} week={week} weekData={weekData} />

      {hasPlans ? <>
        <SectionDivider spacing="compact" tone="soft" />
        <SectionHeading detail={`${weekData?.foods_count ?? weekData?.foods?.length ?? 28} alimentos`} title="Alimentos en esta semana" />
        <FoodPanels items={weekData ? (weekData.foods ?? []).map(foodItem) : weekFoodItems} />
      </> : null}
    </View>
  );
}

type ProgramDetailPreviewProps = {
  footer?: ReactNode;
  item?: LibraryItem;
  onAddWeek?: () => void;
  onAssignDailyPlan?: (week: number, day: number) => void;
  onDuplicateWeek?: (week: number) => Promise<void>;
  onRemoveDailyPlan?: (week: number, day: number) => Promise<void>;
  onRemoveWeek?: (week: number) => Promise<void>;
  onReorderWeeks?: (weeks: number[]) => Promise<void>;
  onScroll?: ScrollViewProps["onScroll"];
  scrollable?: boolean;
};

export function ProgramDetailPreview({ footer, item, onAddWeek, onAssignDailyPlan, onDuplicateWeek, onRemoveDailyPlan, onRemoveWeek, onReorderWeeks, onScroll, scrollable = false }: ProgramDetailPreviewProps = {}) {
  const [activeWeek, setActiveWeek] = useState(1);
  const liveWeeks = item?.panel.kind === "weeks" ? item.panel.weeks : [];
  const displayedWeeks = liveWeeks.length ? liveWeeks.map((week) => week.week_number) : item ? [1] : [1, 2];
  const displayedActiveWeek = displayedWeeks.includes(activeWeek) ? activeWeek : displayedWeeks[0] ?? 1;
  const liveSummaries: ProgramWeekSummary[] = liveWeeks.map((week) => { const filledDays = week.filled_days_count ?? week.days.filter((day) => day.plan_name).length; return { allocation: { protein: week.protein_allocation, carbs: week.carbs_allocation, fat: week.fat_allocation }, averageCalories: week.average_calories ?? week.calories / Math.max(filledDays, 1), calories: week.calories, carbsGrams: week.carbs_grams, dailyPlans: filledDays, fatGrams: week.fat_grams, id: week.id, proteinGrams: week.protein_grams, week: week.week_number }; });
  const selectedWeek = liveWeeks.find((week) => week.week_number === displayedActiveWeek);
  const liveMetrics = liveWeeks.length ? programDailyMetricData(liveWeeks) : undefined;
  const weeksCount = liveWeeks.length || (item ? 1 : 2);
  const livePlansCount = liveWeeks.reduce((sum, week) => sum + (week.filled_days_count ?? week.days.filter((day) => day.plan_name).length), 0);
  const liveFoodsCount = liveWeeks.reduce((maximum, week) => Math.max(maximum, week.foods_count ?? week.foods?.length ?? 0), 0);
  const plansCount = item ? livePlansCount : 12;
  const foodsCount = item ? liveFoodsCount : 36;
  const showProgramStructure = !item || plansCount > 0 || weeksCount > 1;
  const showProgramComparison = !item || weeksCount > 1;

  const overview = (
    <View style={styles.overview}>
        <EntityHeading
          entity="program"
          indicators={showProgramStructure ? [
            { label: "semanas", value: `${weeksCount} SEMANAS` },
            { icon: "dailyPlan", label: "planes asignados", value: plansCount },
            { icon: "food", label: "alimentos", value: foodsCount },
          ] : undefined}
          title={item?.name ?? "Programa de recomposición"}
          variant="page"
        />

        {showProgramComparison ? <>
          <ProgramMetricPreview axisLabels={liveWeeks.map((week) => `S${week.week_number}`)} data={liveMetrics} days={liveMetrics?.length ?? 14} style={layoutStyles.cardContentBleed} />
          <SectionHeading title="Tabla de comparación entre semanas" />
          <ProgramWeekComparisonPanels onDelete={onRemoveWeek} onDuplicate={onDuplicateWeek} onReorder={onReorderWeeks} weeks={liveSummaries.length ? liveSummaries : weekSummaries} />
        </> : null}
        {onAddWeek ? <Button bleed label="+ Agregar nueva semana" onPress={onAddWeek} /> : null}
    </View>
  );

  const planningHeader = (
    <SectionHeading
      detail={`${weeksCount} ${weeksCount === 1 ? "semana" : "semanas"}`}
      title="Planificación semanal"
    />
  );

  const weekTabs = (
    <View
      style={scrollable ? styles.weekTabsSticky : styles.weekTabsEmbedded}>
      <ProgramWeekTabs activeWeek={displayedActiveWeek} onChange={setActiveWeek} weeks={displayedWeeks} />
    </View>
  );

  if (scrollable) {
    return (
      <ScrollView
        contentContainerStyle={styles.screenContent}
        onScroll={onScroll}
        scrollEventThrottle={16}
        stickyHeaderIndices={[3]}
        style={styles.screen}>
        {overview}
        <SectionDivider spacing="wide" />
        <View style={styles.planningHeaderScreen}>{planningHeader}</View>
        {weekTabs}
        <ProgramWeekDetail canRemoveWeek={weeksCount > 1} onAssignDailyPlan={onAssignDailyPlan} onDuplicateWeek={onDuplicateWeek} onRemoveDailyPlan={onRemoveDailyPlan} onRemoveWeek={onRemoveWeek} week={displayedActiveWeek} weekData={selectedWeek} />
        {footer ? <View style={styles.footer}>{footer}</View> : null}
      </ScrollView>
    );
  }

  return (
    <View style={styles.page}>
      {overview}
      <SectionDivider />
      <View style={styles.planningSection}>
        {planningHeader}
        {weekTabs}
        <ProgramWeekDetail canRemoveWeek={weeksCount > 1} onAssignDailyPlan={onAssignDailyPlan} onDuplicateWeek={onDuplicateWeek} onRemoveDailyPlan={onRemoveDailyPlan} onRemoveWeek={onRemoveWeek} week={displayedActiveWeek} weekData={selectedWeek} />
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
  planningHeaderScreen: { marginBottom: tokens.spacing.md },
  weekTabsSticky: { backgroundColor: tokens.color.surfaceApp, marginHorizontal: -tokens.spacing.screen, paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.sm, zIndex: 2 },
  weekTabsEmbedded: { paddingBottom: tokens.spacing.sm },
  footer: { gap: tokens.spacing.lg, marginTop: tokens.spacing.xl },
  weekContent: { gap: tokens.spacing.lg, minWidth: 0, paddingTop: tokens.spacing.md, width: "100%" },
  weekCardHeader: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  weekIdentity: { alignItems: "flex-start", flex: 1, gap: tokens.spacing.sm, minWidth: 0 },
  compactAction: { alignItems: "center", height: 34, justifyContent: "center", width: 34 },
  pressed: { opacity: 0.68 },
});
