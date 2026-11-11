import { type Href, useFocusEffect, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import type { ReactNode } from "react";
import { StyleSheet, View } from "react-native";
import { useCallback, useState } from "react";

import type { DailyPlanSnapshot, EntitlementsData, MealExecutionItem } from "@/api/types";
import { NutritionEntityCard } from "@/components/nutrition";
import { FoodPanels, MealPanels, type MealPanelEditing, type MealPanelItem } from "@/components/panels";
import { Button, EntityCardAction, HeaderMetadataChip } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { snapshotCalories, snapshotDailyPlanFoodPanelItems, snapshotMacroDistribution, snapshotMealPanelItem } from "./presentation-adapters";
import { DailyMealCompletionCard, DailySupplementCompletionCard } from "./meal-completion-summary";
import { normalizeMealExecution } from "./meal-execution";
import { CalendarizedEntityActions } from "./calendarized-entity-actions";
import { ContextualLibraryActions } from "@/components/libraries/contextual-library-actions";
import { SupplementIntakePanel } from "@/components/supplements/supplement-intake-panel";

type ApiRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

type Props = {
  additionalActions?: ReactNode;
  showLibraryActions?: boolean;
  dayId: number | null;
  dateLabel: string;
  eyebrow: string;
  mealExecution?: MealExecutionItem[] | null;
  editing?: MealPanelEditing;
  initialPanelExpanded?: boolean;
  onChangeMealTime?: (meal: MealPanelItem, hour: string) => Promise<void>;
  onAddMeal?: () => void;
  onRemoveFromCalendar?: () => Promise<void>;
  onRenameCalendarized?: (name: string) => Promise<void>;
  onReplacePlan?: () => void;
  onMovePlan?: () => Promise<void> | void;
  calendarDate?: string;
  localToday?: string;
  sourceKind?: "program" | "manual" | null;
  calendarActionsDisabled?: boolean;
  planName?: string;
  snapshot: DailyPlanSnapshot;
  apiRequest: ApiRequest;
  onChanged(): Promise<void> | void;
};

export function CalendarizedDailyPlanCard({ additionalActions, apiRequest, dayId, dateLabel, editing, eyebrow, initialPanelExpanded = false, mealExecution = [], onAddMeal, onChangeMealTime, onChanged, onRemoveFromCalendar, onRenameCalendarized, onReplacePlan, onMovePlan, calendarDate, localToday, sourceKind, calendarActionsDisabled, planName, showLibraryActions = true, snapshot }: Props) {
  const router = useRouter();
  const [timeChangeMeal, setTimeChangeMeal] = useState<MealPanelItem | null>(null);
  const sourceSupplementIntakes = snapshot.supplement_intakes;
  const [entitlementSupplementAccess, setEntitlementSupplementAccess] = useState<boolean | null>(null);
  const [supplementIntakes, setSupplementIntakes] = useState(sourceSupplementIntakes ?? []);
  const canUseSupplements = entitlementSupplementAccess === true;
  useFocusEffect(useCallback(() => {
    let active = true;
    void apiRequest<EntitlementsData>("/api/v1/entitlements").then((data) => {
      if (active) {
        setEntitlementSupplementAccess(Boolean(data.workspace_features?.can_use_supplements));
      }
    }).catch(() => { if (active) setEntitlementSupplementAccess(false); });
    return () => { active = false; };
  }, [apiRequest]));
  const meals = snapshot.meals ?? [];
  const foodsCount = meals.reduce((total, meal) => total + (meal.foods?.length ?? 0), 0);
  const supplementsCount = supplementIntakes.reduce((total, intake) => total + intake.items.length, 0);
  const totals = snapshot.totals;
  const totalCalories = snapshotCalories(totals);
  const mealKeys = new Set(meals.flatMap((meal) => meal.key ? [meal.key] : []));
  const normalizedMealExecution = normalizeMealExecution(mealExecution);
  const executions = normalizedMealExecution.filter((item) => mealKeys.has(item.meal_key));
  const completedMealKeys = new Set(executions.filter((item) => item.status === "completed").map((item) => item.meal_key));
  const mealItems = meals.map((meal, index) => ({
    ...snapshotMealPanelItem(meal, index, totals),
    completed: Boolean(meal.key && completedMealKeys.has(meal.key)),
  }));
  const foods = snapshotDailyPlanFoodPanelItems(meals);
  const cardEditing = editing && onChangeMealTime ? { ...editing, onChangeTime: setTimeChangeMeal } : editing;
  const openDetail = dayId ? () => router.push(`/program/days/${dayId}` as Href) : undefined;
  const sourceDailyPlanId = snapshot.source?.dailyplan_id ?? undefined;
  const movePlan = calendarDate && localToday && onMovePlan ? {
    sourceDate: calendarDate,
    localToday,
    disabled: sourceKind !== "manual" || calendarDate < localToday,
    onMoved: onMovePlan,
  } : undefined;
  return (<>
    <NutritionEntityCard
      actions={<>
        {additionalActions}
        {showLibraryActions && (sourceDailyPlanId || onRemoveFromCalendar) ? <ContextualLibraryActions
          apiRequest={apiRequest}
          calendarActionsDisabled={calendarActionsDisabled}
          entity="dailyPlan"
          id={sourceDailyPlanId}
          movePlan={movePlan}
          name={snapshot.name ?? planName ?? "Minuta diaria"}
          onChanged={onChanged}
          onRemoveFromCalendar={onRemoveFromCalendar}
          onRenameCalendarized={onRenameCalendarized}
          onReplacePlan={onReplacePlan}
          sourceActionsDisabled={sourceKind === "program"}
        /> : null}
        {openDetail ? <EntityCardAction label="Ir al detalle del plan calendarizado" onPress={openDetail} role="link"><ChevronRight color={tokens.color.textMuted} size={17} /></EntityCardAction> : null}
      </>}
      afterNutrition={meals.length ? <DailyMealCompletionCard mealExecution={mealExecution} mealKeys={meals.map((meal) => meal.key)} mealNutrition={meals.map((meal) => ({ calories: snapshotCalories(meal.totals), carbsGrams: meal.totals?.carbs_g ?? 0, fatGrams: meal.totals?.fat_g ?? 0, key: meal.key, proteinGrams: meal.totals?.protein_g ?? 0 }))} /> : undefined}
      completion={{ noteCount: executions.filter((item) => item.note.trim()).length }}
      collapsiblePanel
      dailyPlanFoodsPanel={<FoodPanels items={foods} nestedScroll onOpenItem={(food) => { if (food.detailId != null) router.push((food.kind === "preparation" ? `/libraries/preparations/${food.detailId}` : `/libraries/foods/${food.detailId}`) as Href); }} showEditTab={false} />}
      entity="dailyPlan"
      eyebrow={eyebrow}
      eyebrowAccessory={<HeaderMetadataChip kind="date" value={dateLabel} />}
      headingLink={openDetail ? { label: "Ir al detalle del plan calendarizado", onPress: openDetail } : undefined}
      initialPanelExpanded={initialPanelExpanded}
      indicators={[
        { icon: "meal", label: "comidas", value: meals.length },
        { icon: "food", label: "componentes", value: foodsCount },
        ...(canUseSupplements && supplementsCount ? [{ icon: "supplement" as const, label: "sups", value: supplementsCount }] : []),
      ]}
      nutrition={{
        calories: totalCalories,
        carbs: { allocation: snapshotMacroDistribution(totals, "carbs_g"), grams: totals?.carbs_g ?? 0 },
        fat: { allocation: snapshotMacroDistribution(totals, "fat_g"), grams: totals?.fat_g ?? 0 },
        protein: { allocation: snapshotMacroDistribution(totals, "protein_g"), grams: totals?.protein_g ?? 0, perKilogram: totals?.protein_per_kilogram ?? null },
      }}
      supplementCompletion={canUseSupplements && supplementIntakes.length ? <DailySupplementCompletionCard intakes={supplementIntakes} /> : undefined}
      supplementPanel={canUseSupplements && dayId != null ? <SupplementIntakePanel calendarizedDayId={dayId} completionEndpoint={`/api/v1/days/${dayId}/supplement-intakes`} dailyPlanId={sourceDailyPlanId ?? 0} intakes={supplementIntakes} onChange={setSupplementIntakes} /> : undefined}
      title={snapshot.name ?? planName ?? "Minuta diaria"}>
      <MealPanels
        editing={cardEditing}
        items={mealItems}
        nestedScroll
        showEditTab={false}
        onOpenItem={(meal) => {
          if (dayId == null || !meal.id) return;
          router.push({
            pathname: "/program/days/[id]/meals/[mealKey]",
            params: { id: String(dayId), mealKey: meal.id },
          } as Href);
        }}
      />
      {onAddMeal ? <View style={styles.addMealAction}><Button label="+ Agregar Comida" onPress={onAddMeal} variant="chipPrimary" /></View> : null}
    </NutritionEntityCard>
    <CalendarizedEntityActions
      entityName={timeChangeMeal?.name ?? "Comida"}
      initialAction="change-time"
      key={timeChangeMeal?.id ?? "closed-card-time-change"}
      onVisibleChange={(visible) => { if (!visible) setTimeChangeMeal(null); }}
      timeChange={timeChangeMeal && onChangeMealTime ? { initialTime: timeChangeMeal.time, onSubmit: (hour) => onChangeMealTime(timeChangeMeal, hour) } : undefined}
      visible={timeChangeMeal != null}
    />
  </>);
}

const styles = StyleSheet.create({
  addMealAction: { marginTop: tokens.spacing.md },
});
