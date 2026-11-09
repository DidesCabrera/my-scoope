import type { LibraryPreparationPanelItem, PreparationDetail, PreparationIngredientDetail } from "@/api/preparations";
import type { LibraryNutrition } from "@/api/types";
import type { FoodPanelItem } from "@/components/panels";
import { preparationStateLabel } from "./preparation-ingredients-card";

function share(value: number, total: number): number {
  return total > 0 ? (value / total) * 100 : 0;
}

export function preparationPanelItem(preparation: LibraryPreparationPanelItem, meal: LibraryNutrition): FoodPanelItem {
  return {
    id: `meal-preparation:${preparation.relation_id}`,
    kind: "preparation",
    detailId: preparation.detail_id,
    relationId: preparation.relation_id,
    name: preparation.name,
    projectedLabel: "Preparación",
    quantity: preparation.selection_mode === "units" ? preparation.selected_units ?? 1 : preparation.quantity_g,
    quantityUnit: preparation.selection_mode === "units" ? preparation.household_label : "g",
    portionDisplayQuantity: preparation.selection_mode === "units" ? preparation.quantity_g : null,
    portionDisplayMeasure: preparation.selection_mode === "units" ? "g" : null,
    calories: preparation.calories,
    calorieShare: share(preparation.calories, meal.calories),
    proteinGrams: preparation.protein_g,
    carbsGrams: preparation.carbs_g,
    fatGrams: preparation.fat_g,
    proteinAllocation: share(preparation.protein_g, meal.protein.grams),
    carbsAllocation: share(preparation.carbs_g, meal.carbs.grams),
    fatAllocation: share(preparation.fat_g, meal.fat.grams),
  };
}

export function ingredientPanelItem(ingredient: PreparationIngredientDetail, index: number, preparation: PreparationDetail): FoodPanelItem {
  return {
    id: `preparation-ingredient:${index}:${ingredient.food_id}`,
    kind: "food",
    detailId: ingredient.food_id,
    name: ingredient.name,
    projectedLabel: ingredient.is_condiment ? `${preparationStateLabel(ingredient.preparation_state)} · Condimento` : preparationStateLabel(ingredient.preparation_state),
    quantity: ingredient.quantity_g,
    quantityUnit: "g",
    calories: ingredient.calories,
    calorieShare: share(ingredient.calories, preparation.nutrition.calories),
    proteinGrams: ingredient.protein_g,
    carbsGrams: ingredient.carbs_g,
    fatGrams: ingredient.fat_g,
    proteinAllocation: share(ingredient.protein_g, preparation.nutrition.protein_g),
    carbsAllocation: share(ingredient.carbs_g, preparation.nutrition.carbs_g),
    fatAllocation: share(ingredient.fat_g, preparation.nutrition.fat_g),
  };
}
