import type { CalendarCommitmentKind } from "@/api/calendar-types";
import type { LibraryFoodPanelItem } from "@/api/types";
import type { FoodPanelItem } from "@/components/panels";
import { tokens } from "@/design/tokens";

export const commitmentKinds: CalendarCommitmentKind[] = ["shopping", "cooking", "training"];

export const commitmentPresentation: Record<CalendarCommitmentKind, { label: string; color: string }> = {
  shopping: { label: "Hacer compras", color: tokens.color.food },
  cooking: { label: "Cocinar", color: tokens.color.meal },
  training: { label: "Entrenar", color: tokens.color.success },
};

export function commitmentFoodPanelItem(food: LibraryFoodPanelItem): FoodPanelItem {
  return {
    id: food.id, detailId: food.detail_id, name: food.name, emoji: food.emoji, visualKey: food.visual_key,
    quantity: food.quantity, quantityUnit: food.quantity_unit, calories: food.calories,
    calorieShare: food.calorie_share, proteinGrams: food.protein_grams,
    proteinPerKilogram: food.protein_per_kilogram, carbsGrams: food.carbs_grams,
    fatGrams: food.fat_grams, proteinAllocation: food.protein_allocation,
    carbsAllocation: food.carbs_allocation, fatAllocation: food.fat_allocation,
  };
}
