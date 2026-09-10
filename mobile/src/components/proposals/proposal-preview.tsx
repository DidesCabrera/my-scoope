import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import type { ProposalDailyPlan, ProposalFact, ProposalFood, ProposalKpis, ProposalMeal } from "@/api/types";
import { NutritionEntityCard } from "@/components/nutrition";
import { FoodPanels, MealPanels, type FoodPanelItem, type MealPanelItem } from "@/components/panels";
import { Card, SectionTitle, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

function number(value: number | null | undefined): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function calories(protein: number, carbs: number, fat: number): number {
  return protein * 4 + carbs * 4 + fat * 9;
}

function allocations(protein: number, carbs: number, fat: number): { protein: number; carbs: number; fat: number } {
  const total = calories(protein, carbs, fat);
  if (total <= 0) return { protein: 0, carbs: 0, fat: 0 };
  return {
    protein: (protein * 4 * 100) / total,
    carbs: (carbs * 4 * 100) / total,
    fat: (fat * 9 * 100) / total,
  };
}

function nutrition(kpis: ProposalKpis | null) {
  const protein = number(kpis?.protein);
  const carbs = number(kpis?.carbs);
  const fat = number(kpis?.fat);
  const calculatedAllocations = allocations(protein, carbs, fat);
  return {
    calories: number(kpis?.total_kcal) || calories(protein, carbs, fat),
    protein: { grams: protein, allocation: number(kpis?.alloc_protein) || calculatedAllocations.protein, perKilogram: kpis?.ppk },
    carbs: { grams: carbs, allocation: number(kpis?.alloc_carbs) || calculatedAllocations.carbs },
    fat: { grams: fat, allocation: number(kpis?.alloc_fat) || calculatedAllocations.fat },
  };
}

function foodPanelItems(meal: ProposalMeal): FoodPanelItem[] {
  const mealCalories = number(meal.kpis?.total_kcal);
  return meal.foods.map((food, index) => {
    const protein = number(food.protein);
    const carbs = number(food.carbs);
    const fat = number(food.fat);
    const foodCalories = number(food.total_kcal) || calories(protein, carbs, fat);
    const macroAllocations = allocations(protein, carbs, fat);
    return {
      id: String(food.food_id ?? `proposed-food-${index}`),
      name: food.food_name || "Alimento",
      quantity: number(food.quantity),
      quantityUnit: food.unit || "g",
      calories: foodCalories,
      calorieShare: mealCalories > 0 ? (foodCalories * 100) / mealCalories : 0,
      proteinGrams: protein,
      carbsGrams: carbs,
      fatGrams: fat,
      proteinAllocation: macroAllocations.protein,
      carbsAllocation: macroAllocations.carbs,
      fatAllocation: macroAllocations.fat,
      projectedLabel: "Propuesto",
    };
  });
}

function mealPanelItems(dailyplan: ProposalDailyPlan): MealPanelItem[] {
  const planCalories = number(dailyplan.kpis?.total_kcal);
  return dailyplan.meals.map((item, index) => {
    const mealNutrition = nutrition(item.meal.kpis);
    return {
      canOpen: true,
      id: String(index),
      name: item.meal.name || `Comida ${index + 1}`,
      note: item.note,
      time: item.hour?.slice(0, 5),
      foods: item.meal.foods.map((food) => ({
        name: food.food_name || "Alimento",
        quantity: number(food.quantity),
        quantityUnit: food.unit || "g",
      })),
      calories: mealNutrition.calories,
      calorieShare: planCalories > 0 ? (mealNutrition.calories * 100) / planCalories : 0,
      proteinGrams: mealNutrition.protein.grams,
      carbsGrams: mealNutrition.carbs.grams,
      fatGrams: mealNutrition.fat.grams,
      proteinAllocation: mealNutrition.protein.allocation,
      carbsAllocation: mealNutrition.carbs.allocation,
      fatAllocation: mealNutrition.fat.allocation,
      projectedLabel: "Propuesta",
    };
  });
}

export function ProposalFacts({ title, facts }: { title: string; facts: ProposalFact[] }) {
  if (!facts.length) return null;
  return (
    <Card muted>
      <SectionTitle title={title} />
      {facts.map((fact, index) => <View key={`${fact.label}-${index}`} style={styles.fact}><Text style={textStyles.muted}>{fact.label}</Text><Text style={textStyles.strong}>{fact.value}</Text></View>)}
    </Card>
  );
}

export function ProposalMealCard({ actions, eyebrow = "Comida propuesta", meal }: { actions?: ReactNode; eyebrow?: string; meal: ProposalMeal }) {
  return (
    <NutritionEntityCard
      actions={actions}
      entity="meal"
      eyebrow={eyebrow}
      indicators={[{ icon: "food", label: "alimentos", value: meal.foods.length }]}
      nutrition={nutrition(meal.kpis)}
      title={meal.name || "Comida"}>
      <FoodPanels items={foodPanelItems(meal)} />
    </NutritionEntityCard>
  );
}

export function ProposalDailyPlanCard({ actions, dailyplan, onOpenMeal }: { actions?: ReactNode; dailyplan: ProposalDailyPlan; onOpenMeal?(index: number): void }) {
  return (
    <NutritionEntityCard
      actions={actions}
      entity="dailyPlan"
      eyebrow="Plan diario propuesto"
      indicators={[
        { icon: "meal", label: "comidas", value: dailyplan.meals.length },
        { icon: "food", label: "alimentos", value: dailyplan.meals.reduce((total, item) => total + item.meal.foods.length, 0) },
      ]}
      nutrition={nutrition(dailyplan.kpis)}
      title={dailyplan.name || "Plan diario"}>
      <MealPanels items={mealPanelItems(dailyplan)} onOpenItem={onOpenMeal ? (item) => onOpenMeal(Number(item.id)) : undefined} />
    </NutritionEntityCard>
  );
}

export function ProposalFoodCard({ actions, food }: { actions?: ReactNode; food: ProposalFood }) {
  const kpis: ProposalKpis = {
    total_kcal: food.total_kcal,
    protein: food.protein,
    carbs: food.carbs,
    fat: food.fat,
    ppk: null,
    alloc_protein: null,
    alloc_carbs: null,
    alloc_fat: null,
  };
  return (
    <NutritionEntityCard
      actions={actions}
      entity="food"
      eyebrow="Alimento"
      indicators={[{ label: food.unit || "g", value: number(food.quantity) }]}
      nutrition={nutrition(kpis)}
      subtitle={`${number(food.quantity)} ${food.unit || "g"}`}
      title={food.food_name || "Alimento"}
    />
  );
}

export const proposalPreviewAdapters = { foodPanelItems, mealPanelItems, nutrition };

const styles = StyleSheet.create({
  fact: { alignItems: "center", borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", paddingTop: 10 },
});
