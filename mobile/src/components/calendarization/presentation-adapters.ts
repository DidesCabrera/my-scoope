import type { LibraryMealPanelItem, MacroTotals, MealSnapshot } from "@/api/types";
import type { FoodPanelItem, MealPanelItem } from "@/components/panels";
import { contextualMacroAllocations } from "@/components/panels/contextual-allocation";

export function snapshotCalories(totals?: MacroTotals): number {
  if (totals?.total_kcal != null) return totals.total_kcal;
  return (totals?.protein_g ?? 0) * 4 + (totals?.carbs_g ?? 0) * 4 + (totals?.fat_g ?? 0) * 9;
}

export function snapshotMacroDistribution(totals: MacroTotals | undefined, macro: "protein_g" | "carbs_g" | "fat_g"): number {
  const factor = macro === "fat_g" ? 9 : 4;
  const total = snapshotCalories(totals);
  return total > 0 ? ((totals?.[macro] ?? 0) * factor / total) * 100 : 0;
}

function inferredWeight(totals?: MacroTotals): number | null {
  const protein = totals?.protein_g ?? 0;
  const ppk = totals?.protein_per_kilogram ?? 0;
  return protein > 0 && ppk > 0 ? protein / ppk : null;
}

export function snapshotMealPanelItem(meal: MealSnapshot, index: number, planTotals?: MacroTotals): MealPanelItem {
  const mealCalories = snapshotCalories(meal.totals);
  const planCalories = snapshotCalories(planTotals);
  return {
    canOpen: Boolean(meal.key),
    calorieShare: planCalories > 0 ? mealCalories / planCalories * 100 : 0,
    calories: mealCalories,
    carbsAllocation: contextualAllocation(meal.totals, planTotals, "carbs_g"),
    carbsGrams: meal.totals?.carbs_g ?? 0,
    detailId: meal.detail_id ?? undefined,
    fatAllocation: contextualAllocation(meal.totals, planTotals, "fat_g"),
    fatGrams: meal.totals?.fat_g ?? 0,
    foods: (meal.foods ?? []).map((food) => ({
      name: food.name ?? "Alimento",
      quantity: food.quantity_g ?? 0,
      quantityUnit: food.quantity_unit ?? "g",
      portionDisplayQuantity: food.portion_display_quantity,
      portionDisplayMeasure: food.portion_display_measure,
    })),
    id: meal.key ?? `meal-${index}`,
    name: meal.name ?? "Comida",
    proteinAllocation: contextualAllocation(meal.totals, planTotals, "protein_g"),
    proteinGrams: meal.totals?.protein_g ?? 0,
    proteinPerKilogram: meal.totals?.protein_per_kilogram ?? null,
    time: meal.hour?.slice(0, 5),
  };
}

export function snapshotFoodPanelItems(meal: MealSnapshot): FoodPanelItem[] {
  const mealCalories = snapshotCalories(meal.totals);
  const currentWeight = inferredWeight(meal.totals);
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
      carbsAllocation: contextualAllocation(totals, meal.totals, "carbs_g"),
      carbsGrams: totals.carbs_g ?? 0,
      fatAllocation: contextualAllocation(totals, meal.totals, "fat_g"),
      fatGrams: totals.fat_g ?? 0,
      detailId: food.component_type === "preparation"
        ? food.source_preparation_id ?? undefined
        : food.detail_id ?? food.source_food_id ?? undefined,
      id: food.key ?? `food-${index}`,
      kind: food.component_type === "preparation" ? "preparation" : "food",
      name: food.name ?? "Alimento",
      proteinAllocation: contextualAllocation(totals, meal.totals, "protein_g"),
      proteinGrams: totals.protein_g ?? 0,
      proteinPerKilogram: food.protein_per_kilogram
        ?? (currentWeight ? (totals.protein_g ?? 0) / currentWeight : null),
      quantity: food.quantity_g ?? 0,
      quantityUnit: food.quantity_unit ?? "g",
      portionDisplayQuantity: food.portion_display_quantity,
      portionDisplayMeasure: food.portion_display_measure,
    };
  });
}

export function snapshotDailyPlanFoodPanelItems(meals: MealSnapshot[]): FoodPanelItem[] {
  const currentWeight = meals.map(({ totals }) => inferredWeight(totals)).find((weight) => weight != null) ?? null;
  const aggregated = new Map<string, {
    carbsGrams: number;
    detailId?: number;
    fatGrams: number;
    kind: "food" | "preparation";
    name: string;
    proteinGrams: number;
    quantity: number;
    quantityUnit: "g" | "ml";
    portionDisplayQuantity?: number;
    portionDisplayMeasure?: string;
  }>();

  meals.forEach((meal) => {
    (meal.foods ?? []).forEach((food) => {
      const name = food.name?.trim() || "Alimento";
      const detailId = food.component_type === "preparation"
        ? food.source_preparation_id ?? undefined
        : food.detail_id ?? food.source_food_id ?? undefined;
      const quantityUnit = food.quantity_unit ?? "g";
      const componentKind = food.component_type === "preparation" ? "preparation" : "food";
      const key = detailId != null
        ? `${componentKind}:${detailId}:${quantityUnit}`
        : `name:${name.toLocaleLowerCase("es-CL")}:${quantityUnit}`;
      const current = aggregated.get(key) ?? {
        carbsGrams: 0,
        detailId,
        fatGrams: 0,
        name,
        kind: componentKind,
        proteinGrams: 0,
        quantity: 0,
        quantityUnit,
        portionDisplayQuantity: 0,
        portionDisplayMeasure: food.portion_display_measure || undefined,
      };
      current.carbsGrams += food.carbs_g ?? 0;
      current.fatGrams += food.fat_g ?? 0;
      current.proteinGrams += food.protein_g ?? 0;
      current.quantity += food.quantity_g ?? 0;
      if (
        current.portionDisplayMeasure
        && food.portion_display_measure === current.portionDisplayMeasure
        && food.portion_display_quantity != null
      ) {
        current.portionDisplayQuantity = (current.portionDisplayQuantity ?? 0) + food.portion_display_quantity;
      } else {
        current.portionDisplayQuantity = undefined;
        current.portionDisplayMeasure = undefined;
      }
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
      id: `plan-food-${key}`,
    };
  });
  const planCalories = rows.reduce((total, food) => total + food.calories, 0);
  const allocations = contextualMacroAllocations(rows);

  return rows.map((food, index) => ({
    calorieShare: planCalories > 0 ? food.calories / planCalories * 100 : 0,
    calories: food.calories,
    carbsAllocation: allocations[index].carbs,
    carbsGrams: food.carbsGrams,
    fatAllocation: allocations[index].fat,
    fatGrams: food.fatGrams,
    detailId: food.detailId,
    id: food.id,
    kind: food.kind,
    name: food.name,
    proteinAllocation: allocations[index].protein,
    proteinGrams: food.proteinGrams,
    proteinPerKilogram: currentWeight ? food.proteinGrams / currentWeight : null,
    quantity: food.quantity,
    quantityUnit: food.quantityUnit,
    portionDisplayQuantity: food.portionDisplayQuantity,
    portionDisplayMeasure: food.portionDisplayMeasure,
  }));
}

export function libraryDailyPlanFoodPanelItems(meals: LibraryMealPanelItem[]): FoodPanelItem[] {
  return snapshotDailyPlanFoodPanelItems(meals.map((meal) => ({
    key: meal.id,
    detail_id: meal.detail_id,
    name: meal.name,
    hour: meal.time,
    note: meal.note,
    totals: {
      carbs_g: meal.carbs_grams,
      fat_g: meal.fat_grams,
      protein_g: meal.protein_grams,
      protein_per_kilogram: meal.protein_per_kilogram,
      total_kcal: meal.calories,
    },
    foods: meal.foods.map((food) => ({
      key: food.id,
      detail_id: food.detail_id,
      name: food.name,
      quantity_g: food.quantity,
      quantity_unit: food.quantity_unit === "ml" ? "ml" : "g",
      portion_display_quantity: food.portion_display_quantity,
      portion_display_measure: food.portion_display_measure,
      protein_g: food.protein_grams,
      protein_per_kilogram: food.protein_per_kilogram,
      carbs_g: food.carbs_grams,
      fat_g: food.fat_grams,
      total_kcal: food.calories,
    })),
  })));
}

function contextualAllocation(
  totals: MacroTotals | undefined,
  contextTotals: MacroTotals | undefined,
  macro: "protein_g" | "carbs_g" | "fat_g",
): number {
  const contribution = totals?.[macro] ?? 0;
  const contextTotal = contextTotals?.[macro] ?? 0;
  return contribution > 0 && contextTotal > 0 ? contribution / contextTotal * 100 : 0;
}
