import type { MacroTotals, MealSnapshot } from "@/api/types";
import type { FoodPanelItem, MealPanelItem } from "@/components/panels";

export function snapshotCalories(totals?: MacroTotals): number {
  if (totals?.total_kcal != null) return totals.total_kcal;
  return (totals?.protein_g ?? 0) * 4 + (totals?.carbs_g ?? 0) * 4 + (totals?.fat_g ?? 0) * 9;
}

export function snapshotAllocation(totals: MacroTotals | undefined, macro: "protein_g" | "carbs_g" | "fat_g"): number {
  const factor = macro === "fat_g" ? 9 : 4;
  const total = snapshotCalories(totals);
  return total > 0 ? ((totals?.[macro] ?? 0) * factor / total) * 100 : 0;
}

export function snapshotMealPanelItem(meal: MealSnapshot, index: number, planCalories: number): MealPanelItem {
  const mealCalories = snapshotCalories(meal.totals);
  return {
    canOpen: Boolean(meal.key),
    calorieShare: planCalories > 0 ? mealCalories / planCalories * 100 : 0,
    calories: mealCalories,
    carbsAllocation: snapshotAllocation(meal.totals, "carbs_g"),
    carbsGrams: meal.totals?.carbs_g ?? 0,
    detailId: meal.detail_id ?? undefined,
    fatAllocation: snapshotAllocation(meal.totals, "fat_g"),
    fatGrams: meal.totals?.fat_g ?? 0,
    foods: (meal.foods ?? []).map((food) => ({ name: food.name ?? "Alimento", quantity: food.quantity_g ?? 0, quantityUnit: "g" })),
    id: meal.key ?? `meal-${index}`,
    name: meal.name ?? "Comida",
    proteinAllocation: snapshotAllocation(meal.totals, "protein_g"),
    proteinGrams: meal.totals?.protein_g ?? 0,
    time: meal.hour?.slice(0, 5),
  };
}

export function snapshotFoodPanelItems(meal: MealSnapshot): FoodPanelItem[] {
  const mealCalories = snapshotCalories(meal.totals);
  return (meal.foods ?? []).map((food, index) => {
    const totals: MacroTotals = {
      carbs_g: food.carbs_g ?? 0,
      fat_g: food.fat_g ?? 0,
      protein_g: food.protein_g ?? 0,
      total_kcal: food.total_kcal ?? undefined,
    };
    const calories = snapshotCalories(totals);
    return {
      calorieShare: mealCalories > 0 ? calories / mealCalories * 100 : 0,
      calories,
      carbsAllocation: snapshotAllocation(totals, "carbs_g"),
      carbsGrams: totals.carbs_g ?? 0,
      fatAllocation: snapshotAllocation(totals, "fat_g"),
      fatGrams: totals.fat_g ?? 0,
      id: food.key ?? `food-${index}`,
      name: food.name ?? "Alimento",
      proteinAllocation: snapshotAllocation(totals, "protein_g"),
      proteinGrams: totals.protein_g ?? 0,
      quantity: food.quantity_g ?? 0,
      quantityUnit: "g",
    };
  });
}

export function snapshotDailyPlanFoodPanelItems(meals: MealSnapshot[]): FoodPanelItem[] {
  const aggregated = new Map<string, {
    carbsGrams: number;
    fatGrams: number;
    name: string;
    proteinGrams: number;
    quantity: number;
  }>();

  meals.forEach((meal) => {
    (meal.foods ?? []).forEach((food) => {
      const name = food.name?.trim() || "Alimento";
      const key = name.toLocaleLowerCase("es-CL");
      const current = aggregated.get(key) ?? {
        carbsGrams: 0,
        fatGrams: 0,
        name,
        proteinGrams: 0,
        quantity: 0,
      };
      current.carbsGrams += food.carbs_g ?? 0;
      current.fatGrams += food.fat_g ?? 0;
      current.proteinGrams += food.protein_g ?? 0;
      current.quantity += food.quantity_g ?? 0;
      aggregated.set(key, current);
    });
  });

  const rows = [...aggregated.entries()].map(([key, food]) => {
    const totals: MacroTotals = {
      carbs_g: food.carbsGrams,
      fat_g: food.fatGrams,
      protein_g: food.proteinGrams,
    };
    return {
      ...food,
      calories: snapshotCalories(totals),
      carbsAllocation: snapshotAllocation(totals, "carbs_g"),
      fatAllocation: snapshotAllocation(totals, "fat_g"),
      id: `plan-food-${key}`,
      proteinAllocation: snapshotAllocation(totals, "protein_g"),
    };
  });
  const planCalories = rows.reduce((total, food) => total + food.calories, 0);

  return rows.map((food) => ({
    calorieShare: planCalories > 0 ? food.calories / planCalories * 100 : 0,
    calories: food.calories,
    carbsAllocation: food.carbsAllocation,
    carbsGrams: food.carbsGrams,
    fatAllocation: food.fatAllocation,
    fatGrams: food.fatGrams,
    id: food.id,
    name: food.name,
    proteinAllocation: food.proteinAllocation,
    proteinGrams: food.proteinGrams,
    quantity: food.quantity,
    quantityUnit: "g",
  }));
}
