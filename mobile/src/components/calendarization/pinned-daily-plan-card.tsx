import { type Href, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { StyleSheet, View } from "react-native";

import type { LibraryItem, MealExecutionItem } from "@/api/types";
import { DailyMealCompletionCard } from "@/components/calendarization/meal-completion-summary";
import { NutritionEntityCard } from "@/components/nutrition";
import { MealPanels, type MealPanelItem } from "@/components/panels";
import { pickerHref } from "@/components/pickers/composition-picker-screen";
import { Button, EntityCard, EntityCardAction } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { libraryNutrition } from "@/components/libraries/presentation-adapters";

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

export function PinnedDailyPlanCard({ item, mealExecution }: { item: LibraryItem; mealExecution: MealExecutionItem[] }) {
  const router = useRouter();
  const addMeal = () => router.push(pickerHref("meal-to-dailyplan", { dailyPlanId: item.id, returnTo: "/today" }));
  const detailAction = (
    <EntityCardAction label="Ir al detalle del plan" onPress={() => router.push(`/libraries/daily-plans/${item.id}` as Href)} role="link">
      <ChevronRight color={tokens.color.textMuted} size={21} />
    </EntityCardAction>
  );
  const meals = item.panel.meals;

  if (meals.length === 0) {
    return (
      <EntityCard actions={detailAction} entity="dailyPlan" eyebrow="PLAN DE HOY" title={item.name}>
        <Button bleed label="+ Agregar Comida" onPress={addMeal} />
      </EntityCard>
    );
  }

  const completedKeys = new Set(mealExecution.filter((entry) => entry.status === "completed").map((entry) => entry.meal_key));
  return (
    <NutritionEntityCard
      actions={detailAction}
      beforeNutrition={<DailyMealCompletionCard mealExecution={mealExecution} mealKeys={meals.map((meal) => meal.id)} />}
      entity="dailyPlan"
      eyebrow="PLAN DE HOY"
      nutrition={libraryNutrition(item.nutrition)}
      title={item.name}>
      <MealPanels
        items={meals.map((meal) => mealPanelItem(meal, completedKeys))}
        onOpenItem={(meal) => {
          if (!meal.detailId || !meal.relationId) return;
          router.push({
            pathname: "/libraries/meals/[id]",
            params: { dailyPlanId: String(item.id), dailyPlanMealId: String(meal.relationId), id: String(meal.detailId), mealKey: meal.id, mealTime: meal.time ?? "", pinned: "1" },
          } as Href);
        }}
      />
      <View style={styles.addMealAction}>
        <Button bleed label="+ Agregar Comida" onPress={addMeal} />
      </View>
    </NutritionEntityCard>
  );
}

const styles = StyleSheet.create({
  addMealAction: { marginTop: tokens.spacing.md },
});
