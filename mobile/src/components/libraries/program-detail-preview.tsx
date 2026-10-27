import { type Href, useRouter } from "expo-router";
import { Calendar1, Carrot, ClipboardList, Copy, MoreHorizontal, Trash2 } from "lucide-react-native";
import type { ReactNode } from "react";
import { useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { NestableScrollContainer } from "react-native-draggable-flatlist";

import { EntityPanelTabs, GroupedFoodsCard, PanelSurface, type FoodPanelItem } from "@/components/panels";
import { SectionHeading } from "@/components/ui/typography";
import { tokens } from "@/design/tokens";
import { isHeaderIdentityVisible } from "@/components/navigation/header-scroll";
import type { LibraryFoodPanelItem, LibraryItem, LibraryWeekPanelItem } from "@/api/types";
import { EntityHeading, layoutStyles, StructuralIndicators } from "@/components/ui";
import { Button } from "@/components/ui/controls";
import { ProgramMetricPreview, programDailyMetricData, WeekMetricPreview, type WeekMetricFilter } from "./program-child-card";
import { ProgramDailyPlanPreview } from "./program-daily-plan-preview";
import { ProgramDaySelector, ProgramWeekHeading, ProgramWeekTabs } from "./program-planning-controls";
import { ProgramWeekComparisonPanels, type ProgramWeekSummary } from "./program-week-comparison-panels";
import { ContextCardActions, type ContextCardAction } from "./context-card-actions";
import { ProgramSectionHeader } from "@/components/programs/program-section-header";

const weekSummaries: ProgramWeekSummary[] = [
  { allocation: { carbs: 47, fat: 29, protein: 24 }, averageCalories: 2040, calories: 14280, carbsGrams: 1546, dailyPlans: 7, fatGrams: 427, id: "week-1", ppk: 1.9, proteinGrams: 1064, week: 1 },
  { allocation: { carbs: 46, fat: 29, protein: 25 }, averageCalories: 2087, calories: 14610, carbsGrams: 1574, dailyPlans: 7, fatGrams: 438, id: "week-2", ppk: 2, proteinGrams: 1108, week: 2 },
];

const dayLabels = ["L", "M", "X", "J", "V", "S", "D"];
const weekMetricTabs: { key: WeekMetricFilter; label: string }[] = [
  { key: "calories", label: "Calorías" },
  { key: "ppk", label: "PPK" },
  { key: "macros", label: "Macros" },
  { key: "allocation", label: "Alloc" },
  { key: "all", label: "Todos" },
];

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

function ProgramDaysGrid({ onAssignDailyPlan, onOpenDailyPlan, onOpenMeal, onRemoveDailyPlan, onSaveDailyPlan, week, weekData }: { onAssignDailyPlan?: (week: number, day: number) => void; onOpenDailyPlan?: (week: number, day: number) => void; onOpenMeal?: (week: number, day: number, mealIndex: number) => void; onRemoveDailyPlan?: (week: number, day: number) => Promise<void>; onSaveDailyPlan?: (week: number, day: number) => Promise<void>; week: number; weekData?: LibraryWeekPanelItem }) {
  const filledDays = weekData ? weekData.days.map((day) => Boolean(day.plan_name)) : week === 1 ? [true, true, true, true, true, false, true] : [true, true, false, true, true, true, true];
  const labels = weekData?.days.map((day) => day.day_label.slice(0, 1).toUpperCase()) ?? dayLabels;
  const [selectedDay, setSelectedDay] = useState<number | null>(() => filledDays[0] ? 0 : null);
  return (
    <ProgramDaySelector
      accessibilityLabel={`Minutas diarias de Semana ${week}`}
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
        onOpen={onOpenDailyPlan ? () => onOpenDailyPlan(week, selectedDay + 1) : undefined}
        onOpenMeal={onOpenMeal ? (mealIndex) => onOpenMeal(week, selectedDay + 1, mealIndex) : undefined}
        onRemove={onRemoveDailyPlan ? () => onRemoveDailyPlan(week, selectedDay + 1) : undefined}
        onReplace={onAssignDailyPlan ? () => onAssignDailyPlan(week, selectedDay + 1) : undefined}
        onSaveToLibrary={onSaveDailyPlan ? () => onSaveDailyPlan(week, selectedDay + 1) : undefined}
        week={week}
      /> : null}
    </ProgramDaySelector>
  );
}

function foodItem(item: LibraryFoodPanelItem): FoodPanelItem {
  return { id: item.id, detailId: item.detail_id, name: item.name, emoji: item.emoji, visualKey: item.visual_key, quantity: item.quantity, quantityUnit: item.quantity_unit, portionDisplayQuantity: item.portion_display_quantity, portionDisplayMeasure: item.portion_display_measure, calories: item.calories, calorieShare: item.calorie_share, proteinGrams: item.protein_grams, proteinPerKilogram: item.protein_per_kilogram, carbsGrams: item.carbs_grams, fatGrams: item.fat_grams, proteinAllocation: item.protein_allocation, carbsAllocation: item.carbs_allocation, fatAllocation: item.fat_allocation };
}

export function ProgramWeekDetail({ canRemoveWeek = false, onAssignDailyPlan, onDuplicateWeek, onOpenDailyPlan, onOpenFood, onOpenMeal, onRemoveDailyPlan, onRemoveWeek, onSaveDailyPlan, showHeading = true, showWeekAnalytics = true, week, weekData }: { canRemoveWeek?: boolean; onAssignDailyPlan?: (week: number, day: number) => void; onDuplicateWeek?: (week: number) => Promise<void>; onOpenDailyPlan?: (week: number, day: number) => void; onOpenFood?: (foodId: number) => void; onOpenMeal?: (week: number, day: number, mealIndex: number) => void; onRemoveDailyPlan?: (week: number, day: number) => Promise<void>; onRemoveWeek?: (week: number) => Promise<void>; onReorderDailyPlans?: (week: number, orderedDays: number[]) => Promise<void>; onSaveDailyPlan?: (week: number, day: number) => Promise<void>; showHeading?: boolean; showWeekAnalytics?: boolean; week: number; weekData?: LibraryWeekPanelItem }) {
  const router = useRouter();
  const [activeMetricTab, setActiveMetricTab] = useState<WeekMetricFilter>("calories");
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
    <View style={[styles.weekContent, !showHeading && styles.weekContentWithoutHeading]}>
      {showHeading ? <View style={styles.weekCardHeader}>
        <View style={styles.weekIdentity}>
          <ProgramWeekHeading week={week} />
          {hasPlans ? <StructuralIndicators
            entity="program"
            indicators={[
              { icon: "dailyPlan", label: "minutas diarias", value: filledDaysCount },
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

      {hasPlans && showWeekAnalytics ? <>
        <View style={styles.weekChartSection}>
          <View style={styles.weekChartPanelGroup}>
            <View style={styles.metricTabsBleed}>
              <EntityPanelTabs activeTab={activeMetricTab} onChange={setActiveMetricTab} tabs={weekMetricTabs} />
            </View>
            <PanelSurface style={styles.weekChartPanel}>
              <View style={styles.weekChartPanelBody}>
                <WeekMetricPreview axisLabels={weekData?.days.map((day) => day.day_label.slice(0, 1).toUpperCase()) ?? dayLabels} axisLeadingLabel="Semana" data={liveMetricData} days={7} filter={activeMetricTab} />
              </View>
            </PanelSurface>
          </View>
        </View>
      </> : null}

      <View style={styles.dailyPlansSectionHeading}>
        <SectionHeading icon={<ClipboardList color={tokens.color.entityIconForeground} size={18} />} title={`Minutas diarias en Semana ${week}`} />
      </View>
      <ProgramDaysGrid key={`${week}:${weekData?.days.map((day) => Number(Boolean(day.plan_name))).join("") ?? "demo"}`} onAssignDailyPlan={onAssignDailyPlan} onOpenDailyPlan={onOpenDailyPlan} onOpenMeal={onOpenMeal} onRemoveDailyPlan={onRemoveDailyPlan} onSaveDailyPlan={onSaveDailyPlan} week={week} weekData={weekData} />

      {hasPlans ? <>
        <View style={styles.foodsSectionHeading}>
          <SectionHeading icon={<Carrot color={tokens.color.entityIconForeground} size={18} />} title={`Alimentos en Semana ${week}`} />
        </View>
        <GroupedFoodsCard title={`Alimentos semana ${week}`} items={weekData ? (weekData.foods ?? []).map(foodItem) : weekFoodItems} onOpenItem={(food) => {
          if (food.detailId == null) return;
          if (onOpenFood) onOpenFood(food.detailId);
          else router.push(`/libraries/foods/${food.detailId}` as Href);
        }} />

      </> : null}
    </View>
  );
}

type ProgramDetailPreviewProps = {
  fallbackWeeksCount?: number;
  footer?: ReactNode;
  footerTopSpacing?: number;
  item?: LibraryItem;
  onAddWeek?: () => void;
  onAssignDailyPlan?: (week: number, day: number) => void;
  onDuplicateWeek?: (week: number) => Promise<void>;
  onOpenDailyPlan?: (week: number, day: number) => void;
  onOpenFood?: (foodId: number) => void;
  onOpenMeal?: (week: number, day: number, mealIndex: number) => void;
  onRemoveDailyPlan?: (week: number, day: number) => Promise<void>;
  onRemoveWeek?: (week: number) => Promise<void>;
  onReorderDailyPlans?: (week: number, orderedDays: number[]) => Promise<void>;
  onReorderWeeks?: (weeks: number[]) => Promise<void>;
  onSaveDailyPlan?: (week: number, day: number) => Promise<void>;
  onHeaderVisibilityChange?: (visible: boolean) => void;
  renderWeekContext?: (week: number) => ReactNode;
  scrollable?: boolean;
  showWeekAnalytics?: boolean;
};

export function ProgramDetailPreview({ fallbackWeeksCount = 2, footer, footerTopSpacing = tokens.spacing.xl, item, onAddWeek, onAssignDailyPlan, onDuplicateWeek, onHeaderVisibilityChange, onOpenDailyPlan, onOpenFood, onOpenMeal, onRemoveDailyPlan, onRemoveWeek, onReorderDailyPlans, onReorderWeeks, onSaveDailyPlan, renderWeekContext, scrollable = false, showWeekAnalytics = true }: ProgramDetailPreviewProps = {}) {
  const [activeWeek, setActiveWeek] = useState(1);
  const liveWeeks = item?.panel.kind === "weeks" ? item.panel.weeks : [];
  const displayedWeeks = liveWeeks.length ? liveWeeks.map((week) => week.week_number) : item ? [1] : Array.from({ length: fallbackWeeksCount }, (_, index) => index + 1);
  const displayedActiveWeek = displayedWeeks.includes(activeWeek) ? activeWeek : displayedWeeks[0] ?? 1;
  const liveSummaries: ProgramWeekSummary[] = liveWeeks.map((week) => { const filledDays = week.filled_days_count ?? week.days.filter((day) => day.plan_name).length; const ppkValues = week.days.flatMap((day) => day.nutrition?.protein.per_kilogram == null ? [] : [day.nutrition.protein.per_kilogram]); return { allocation: { protein: week.protein_allocation, carbs: week.carbs_allocation, fat: week.fat_allocation }, averageCalories: week.average_calories ?? week.calories / Math.max(filledDays, 1), calories: week.calories, carbsGrams: week.carbs_grams, dailyPlans: filledDays, fatGrams: week.fat_grams, id: week.id, ppk: ppkValues.length ? ppkValues.reduce((sum, value) => sum + value, 0) / ppkValues.length : null, proteinGrams: week.protein_grams, week: week.week_number }; });
  const selectedWeek = liveWeeks.find((week) => week.week_number === displayedActiveWeek);
  const liveMetrics = liveWeeks.length ? programDailyMetricData(liveWeeks) : undefined;
  const weeksCount = liveWeeks.length || (item ? 1 : fallbackWeeksCount);
  const livePlansCount = liveWeeks.reduce((sum, week) => sum + (week.filled_days_count ?? week.days.filter((day) => day.plan_name).length), 0);
  const liveFoodsCount = liveWeeks.reduce((maximum, week) => Math.max(maximum, week.foods_count ?? week.foods?.length ?? 0), 0);
  const plansCount = item ? livePlansCount : 12;
  const foodsCount = item ? liveFoodsCount : 36;
  const showProgramStructure = !item || plansCount > 0 || weeksCount > 1;
  const showProgramComparison = !item || weeksCount > 1;
  const singleWeekPlanningSpacing = weeksCount === 1 ? 32 - tokens.spacing.xl : undefined;
  const addWeekAtEnd = Boolean(onAddWeek && weeksCount === 1);
  const addWeekButton = onAddWeek ? <Button label="+ Agregar nueva semana" onPress={onAddWeek} variant="chipPrimary" /> : null;

  const overview = (
    <View style={styles.overview}>
        <EntityHeading
          entity="program"
          indicators={showProgramStructure ? [
            { label: "semanas", value: `${weeksCount} SEMANAS` },
            { icon: "dailyPlan", label: "minutas asignadas", value: plansCount },
            { icon: "food", label: "alimentos", value: foodsCount },
          ] : undefined}
          title={item?.name ?? "Programa de recomposición"}
          variant="page"
        />

        {showProgramComparison ? <>
          <ProgramMetricPreview axisLabels={(liveWeeks.length ? liveWeeks.map((week) => week.week_number) : displayedWeeks).map((week) => `S${week}`)} data={liveMetrics} days={liveMetrics?.length ?? 14} style={layoutStyles.cardContentBleed} />
          <SectionHeading title="Composición programa" />
          <ProgramWeekComparisonPanels onDelete={onRemoveWeek} onDuplicate={onDuplicateWeek} onReorder={onReorderWeeks} weeks={liveSummaries.length ? liveSummaries : weekSummaries} />
        </> : null}
        {!addWeekAtEnd ? addWeekButton : null}
    </View>
  );

  const planningHeader = (
    <ProgramSectionHeader
      icon={Calendar1}
      subtitle="Recorre las semanas de tu programa y conoce las minutas diarias y los alimentos de cada una."
      title="Planificación Semanal"
      topSpacing={singleWeekPlanningSpacing}
    />
  );

  const weekTabs = (
    <View
      style={scrollable ? styles.weekTabsSticky : styles.weekTabsEmbedded}>
      <ProgramWeekTabs activeWeek={displayedActiveWeek} onChange={setActiveWeek} style={styles.weekTabsBarBleed} weeks={displayedWeeks} />
    </View>
  );
  const bottomActions = addWeekAtEnd || footer
    ? <View style={[styles.footer, { marginTop: footerTopSpacing }]}>{addWeekAtEnd ? addWeekButton : null}{footer}</View>
    : null;

  if (scrollable) {
    return (
      <NestableScrollContainer
        contentContainerStyle={styles.screenContent}
        onScroll={({ nativeEvent }) => onHeaderVisibilityChange?.(isHeaderIdentityVisible(nativeEvent.contentOffset.y))}
        scrollEventThrottle={16}
        showsVerticalScrollIndicator={false}
        stickyHeaderIndices={[2]}
        style={styles.screen}>
        {overview}
        <View style={[styles.planningHeaderScreen, weeksCount === 1 && styles.singleWeekPlanningHeaderScreen]}>{planningHeader}</View>
        {weekTabs}
        {renderWeekContext?.(displayedActiveWeek)}
        <ProgramWeekDetail canRemoveWeek={weeksCount > 1} onAssignDailyPlan={onAssignDailyPlan} onDuplicateWeek={onDuplicateWeek} onOpenDailyPlan={onOpenDailyPlan} onOpenFood={onOpenFood} onOpenMeal={onOpenMeal} onRemoveDailyPlan={onRemoveDailyPlan} onRemoveWeek={onRemoveWeek} onReorderDailyPlans={onReorderDailyPlans} onSaveDailyPlan={onSaveDailyPlan} showWeekAnalytics={showWeekAnalytics} week={displayedActiveWeek} weekData={selectedWeek} />
        {bottomActions}
      </NestableScrollContainer>
    );
  }

  return (
    <View style={styles.page}>
      {overview}
      <View style={styles.planningSection}>
        {planningHeader}
        {weekTabs}
        {renderWeekContext?.(displayedActiveWeek)}
        <ProgramWeekDetail canRemoveWeek={weeksCount > 1} onAssignDailyPlan={onAssignDailyPlan} onDuplicateWeek={onDuplicateWeek} onOpenDailyPlan={onOpenDailyPlan} onOpenFood={onOpenFood} onOpenMeal={onOpenMeal} onRemoveDailyPlan={onRemoveDailyPlan} onRemoveWeek={onRemoveWeek} onReorderDailyPlans={onReorderDailyPlans} onSaveDailyPlan={onSaveDailyPlan} showWeekAnalytics={showWeekAnalytics} week={displayedActiveWeek} weekData={selectedWeek} />
        {bottomActions}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  screenContent: { flexGrow: 1, paddingBottom: 96, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  page: { gap: tokens.spacing.xl, minWidth: 0, width: "100%" },
  overview: { gap: tokens.spacing.lg, minWidth: 0 },
  planningSection: { gap: 0, minWidth: 0 },
  planningHeaderScreen: { marginTop: tokens.spacing.lg + 24 },
  singleWeekPlanningHeaderScreen: { marginTop: tokens.spacing.xl },
  weekTabsSticky: { backgroundColor: tokens.color.surfaceApp, marginHorizontal: -tokens.spacing.screen, paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.sm, zIndex: 2 },
  weekTabsEmbedded: { paddingBottom: tokens.spacing.sm },
  weekTabsBarBleed: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  footer: { gap: tokens.spacing.lg },
  weekContent: { gap: tokens.spacing.lg, minWidth: 0, paddingTop: tokens.spacing.md + tokens.spacing.sm, width: "100%" },
  weekContentWithoutHeading: { paddingTop: 0 },
  weekChartSection: { gap: tokens.spacing.md, minWidth: 0 },
  weekChartPanelGroup: { gap: tokens.spacing.xs },
  metricTabsBleed: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding - tokens.spacing.sm },
  weekChartPanel: { backgroundColor: tokens.color.surfaceCard, marginHorizontal: -tokens.spacing.screen },
  weekChartPanelBody: { paddingBottom: tokens.spacing.lg, paddingHorizontal: tokens.layout.reducedInset, paddingTop: tokens.spacing.sm },
  weekCardHeader: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  weekIdentity: { alignItems: "flex-start", flex: 1, gap: tokens.spacing.sm, minWidth: 0 },
  dailyPlansSectionHeading: { marginTop: tokens.spacing.md },
  foodsSectionHeading: { marginTop: tokens.spacing.xxl },
  compactAction: { alignItems: "center", height: 34, justifyContent: "center", width: 34 },
  pressed: { opacity: 0.68 },
});
