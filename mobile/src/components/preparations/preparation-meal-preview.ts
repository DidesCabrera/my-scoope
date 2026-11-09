import type { PreparationDetail } from "@/api/preparations";
import type { LibraryItem, LibraryNutrition } from "@/api/types";
import type { FoodPanelItem } from "@/components/panels";

type MealForPreview = Pick<LibraryItem, "name" | "nutrition" | "panel">;

function share(value: number, total: number): number {
  return total > 0 ? value / total * 100 : 0;
}

function selectedRow(detail: PreparationDetail, relationId?: number): FoodPanelItem {
  return {
    id: `preview-preparation:${detail.id}`,
    kind: "preparation",
    detailId: detail.id,
    relationId,
    name: detail.name,
    quantity: detail.selection_mode === "units" ? detail.selected_units ?? 1 : detail.grams,
    quantityUnit: detail.selection_mode === "units" ? detail.household_label : "g",
    portionDisplayQuantity: detail.selection_mode === "units" ? detail.grams : null,
    portionDisplayMeasure: detail.selection_mode === "units" ? "g" : null,
    calories: detail.nutrition.calories,
    proteinGrams: detail.nutrition.protein_g,
    carbsGrams: detail.nutrition.carbs_g,
    fatGrams: detail.nutrition.fat_g,
    projectedLabel: relationId ? "Por actualizar" : "Por agregar",
    calorieShare: 0,
    proteinAllocation: 0,
    carbsAllocation: 0,
    fatAllocation: 0,
  };
}

export function projectPreparationMeal(meal: MealForPreview, selected: PreparationDetail, relationId?: number) {
  if (meal.panel.kind !== "foods") return null;
  const preparations = meal.panel.preparations ?? [];
  const replaced = relationId == null ? undefined : preparations.find((row) => row.relation_id === relationId);
  if (relationId != null && !replaced) return null;

  const base = meal.nutrition;
  const contribution = selected.nutrition;
  const calories = Math.max(0, base.calories - (replaced?.calories ?? 0) + contribution.calories);
  const proteinGrams = Math.max(0, base.protein.grams - (replaced?.protein_g ?? 0) + contribution.protein_g);
  const carbsGrams = Math.max(0, base.carbs.grams - (replaced?.carbs_g ?? 0) + contribution.carbs_g);
  const fatGrams = Math.max(0, base.fat.grams - (replaced?.fat_g ?? 0) + contribution.fat_g);
  const macroCalories = proteinGrams * 4 + carbsGrams * 4 + fatGrams * 9;
  const perKilogram = base.protein.per_kilogram != null && base.protein.grams > 0
    ? proteinGrams * base.protein.per_kilogram / base.protein.grams
    : null;
  const nutrition: LibraryNutrition = {
    calories,
    protein: { grams: proteinGrams, allocation: share(proteinGrams * 4, macroCalories), per_kilogram: perKilogram },
    carbs: { grams: carbsGrams, allocation: share(carbsGrams * 4, macroCalories) },
    fat: { grams: fatGrams, allocation: share(fatGrams * 9, macroCalories) },
  };

  const foods: FoodPanelItem[] = meal.panel.foods.map((row) => ({
    id: row.id,
    kind: "food",
    detailId: row.detail_id,
    relationId: row.relation_id,
    name: row.name,
    emoji: row.emoji,
    visualKey: row.visual_key,
    quantity: row.quantity,
    quantityUnit: row.quantity_unit,
    portionDisplayQuantity: row.portion_display_quantity,
    portionDisplayMeasure: row.portion_display_measure,
    calories: row.calories,
    proteinGrams: row.protein_grams,
    proteinPerKilogram: row.protein_per_kilogram,
    carbsGrams: row.carbs_grams,
    fatGrams: row.fat_grams,
    calorieShare: 0,
    proteinAllocation: 0,
    carbsAllocation: 0,
    fatAllocation: 0,
  }));
  const candidate = selectedRow(selected, relationId);
  const preparationRows: FoodPanelItem[] = preparations.map((row) => row.relation_id === relationId ? candidate : ({
    id: `meal-preparation:${row.relation_id}`,
    kind: "preparation",
    detailId: row.detail_id,
    relationId: row.relation_id,
    name: row.name,
    quantity: row.selection_mode === "units" ? row.selected_units ?? 1 : row.quantity_g,
    quantityUnit: row.selection_mode === "units" ? row.household_label : "g",
    portionDisplayQuantity: row.selection_mode === "units" ? row.quantity_g : null,
    portionDisplayMeasure: row.selection_mode === "units" ? "g" : null,
    calories: row.calories,
    proteinGrams: row.protein_g,
    carbsGrams: row.carbs_g,
    fatGrams: row.fat_g,
    calorieShare: 0,
    proteinAllocation: 0,
    carbsAllocation: 0,
    fatAllocation: 0,
  }));
  if (!replaced) preparationRows.push(candidate);

  return {
    name: meal.name,
    nutrition,
    contribution,
    foodCount: foods.length,
    preparationCount: preparationRows.length,
    items: [...foods, ...preparationRows].map((item) => ({
      ...item,
      calorieShare: share(item.calories, calories),
      proteinAllocation: share(item.proteinGrams, proteinGrams),
      carbsAllocation: share(item.carbsGrams, carbsGrams),
      fatAllocation: share(item.fatGrams, fatGrams),
    })),
  };
}
