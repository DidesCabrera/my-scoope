import { type Href, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { useState } from "react";

import type { LibraryItem, MealExecutionItem } from "@/api/types";
import { DailyMealCompletionCard, DailySupplementCompletionCard } from "@/components/calendarization/meal-completion-summary";
import { CalendarizedEntityActions } from "@/components/calendarization/calendarized-entity-actions";
import { normalizeMealExecution } from "@/components/calendarization/meal-execution";
import { NutritionEntityCard } from "@/components/nutrition";
import { MealPanels, type MealPanelEditing, type MealPanelItem } from "@/components/panels";
import { pickerHref } from "@/components/pickers/composition-picker-screen";
import { Button, EntityCardAction } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { libraryNutrition } from "@/components/libraries/presentation-adapters";
import { ContextualLibraryActions } from "@/components/libraries/contextual-library-actions";
import { FoodPanels as LibraryFoodPanels } from "@/components/libraries/entity-panels";
import { SupplementIntakePanel } from "@/components/supplements/supplement-intake-panel";
import { SupplementProSheet } from "@/components/supplements/supplement-pro-sheet";

type ApiRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

function mealPanelItem(item: LibraryItem["panel"]["meals"][number], completedKeys: Set<string>): MealPanelItem {
  return {
    id: item.id,
    relationId: item.relation_id,
    detailId: item.detail_id,
    name: item.name,
    time: item.time?.slice(0, 5),
    note: item.note,
    foods: item.foods.map((food) => ({ name: food.name, quantity: food.quantity, quantityUnit: food.quantity_unit })),
    calories: item.calories,
    calorieShare: item.calorie_share,
    proteinGrams: item.protein_grams,
    proteinPerKilogram: item.protein_per_kilogram,
    carbsGrams: item.carbs_grams,
    fatGrams: item.fat_grams,
    proteinAllocation: item.protein_allocation,
    carbsAllocation: item.carbs_allocation,
    fatAllocation: item.fat_allocation,
    completed: completedKeys.has(item.id),
  };
}

export function PinnedDailyPlanCard({ apiRequest, editing, initialPanelExpanded = false, item, mealExecution, onChangeMealTime, onChanged }: { apiRequest: ApiRequest; editing?: MealPanelEditing; initialPanelExpanded?: boolean; item: LibraryItem; mealExecution?: MealExecutionItem[] | null; onChangeMealTime?: (meal: MealPanelItem, hour: string) => Promise<void>; onChanged(): Promise<void> | void }) {
  const router = useRouter();
  const [timeChangeMeal, setTimeChangeMeal] = useState<MealPanelItem | null>(null);
  const [supplementUpsell, setSupplementUpsell] = useState(false);
  const sourceSupplementIntakes = item.panel.supplement_intakes;
  const [supplementIntakes, setSupplementIntakes] = useState(sourceSupplementIntakes ?? []);
  const addMeal = () => router.push(pickerHref("meal-to-dailyplan", { dailyPlanId: item.id, returnTo: "/today" }));
  const openDetail = () => router.push(`/libraries/daily-plans/${item.id}?origin=home` as Href);
  const detailAction = (<>
    <ContextualLibraryActions apiRequest={apiRequest} entity="dailyPlan" id={item.id} name={item.name} onChanged={onChanged} />
    <EntityCardAction label="Ir al detalle del plan" onPress={openDetail} role="link">
      <ChevronRight color={tokens.color.textMuted} size={17} />
    </EntityCardAction>
  </>);
  const meals = item.panel.meals;
  const supplementsCount = supplementIntakes.reduce((total, intake) => total + intake.items.length, 0);
  const indicators = [
    { icon: "meal" as const, label: "comidas", value: meals.length },
    { icon: "food" as const, label: "alimentos", value: meals.reduce((total, meal) => total + meal.foods.length, 0) },
    ...(supplementsCount ? [{ icon: "supplement" as const, label: "sups", value: supplementsCount }] : []),
  ];

  const normalizedMealExecution = normalizeMealExecution(mealExecution);
  const completedKeys = new Set(normalizedMealExecution.filter((entry) => entry.status === "completed").map((entry) => entry.meal_key));
  const cardEditing = editing && onChangeMealTime ? { ...editing, onChangeTime: setTimeChangeMeal } : editing;
  return (<>
    <NutritionEntityCard
      actions={detailAction}
      afterNutrition={meals.length ? <DailyMealCompletionCard mealExecution={normalizedMealExecution} mealKeys={meals.map((meal) => meal.id)} mealNutrition={meals.map((meal) => ({ calories: meal.calories, carbsGrams: meal.carbs_grams, fatGrams: meal.fat_grams, key: meal.id, proteinGrams: meal.protein_grams }))} /> : undefined}
      collapsiblePanel
      dailyPlanFoodsPanel={<LibraryFoodPanels items={item.panel.foods} nestedScroll showEditTab={false} />}
      entity="dailyPlan"
      eyebrow="Minuta del día"
      headingLink={{ label: "Ir al detalle del plan", onPress: openDetail }}
      initialPanelExpanded={initialPanelExpanded}
      indicators={indicators}
      nutrition={libraryNutrition(item.nutrition)}
      onLockedSupplementPress={item.supplements_available && !item.can_use_supplements ? () => setSupplementUpsell(true) : undefined}
      supplementCompletion={item.can_use_supplements && supplementIntakes.length ? <DailySupplementCompletionCard intakes={supplementIntakes} /> : undefined}
      supplementPanel={item.can_use_supplements ? <SupplementIntakePanel completionEndpoint="/api/v1/today/pinned-plan/supplement-intakes" dailyPlanId={item.id} editable intakes={supplementIntakes} onChange={setSupplementIntakes} pinned /> : undefined}
      title={item.name}>
      <MealPanels
        editing={cardEditing}
        items={meals.map((meal) => mealPanelItem(meal, completedKeys))}
        nestedScroll
        showEditTab={false}
        onOpenItem={(meal) => {
          if (!meal.detailId || !meal.relationId) return;
          router.push({
            pathname: "/libraries/meals/[id]",
            params: { dailyPlanId: String(item.id), dailyPlanMealId: String(meal.relationId), id: String(meal.detailId), mealKey: meal.id, mealTime: meal.time ?? "", pinned: "1" },
          } as Href);
        }}
      />
      <View style={styles.addMealAction}>
        <Button label="+ Agregar Comida" onPress={addMeal} variant="chipPrimary" />
      </View>
    </NutritionEntityCard>
    <CalendarizedEntityActions entityName={timeChangeMeal?.name ?? "Comida"} initialAction="change-time" key={timeChangeMeal?.id ?? "closed-card-time-change"} onVisibleChange={(visible) => { if (!visible) setTimeChangeMeal(null); }} timeChange={timeChangeMeal && onChangeMealTime ? { initialTime: timeChangeMeal.time, onSubmit: (hour) => onChangeMealTime(timeChangeMeal, hour) } : undefined} visible={timeChangeMeal != null} />
    <SupplementProSheet onClose={() => setSupplementUpsell(false)} visible={supplementUpsell} />
  </>);
}

const styles = StyleSheet.create({
  addMealAction: { marginTop: tokens.spacing.md },
});
