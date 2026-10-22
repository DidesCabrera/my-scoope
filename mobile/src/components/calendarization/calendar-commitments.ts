import type { CalendarCommitmentKind } from "@/api/calendar-types";
import { CookingPot, Dumbbell, ShoppingBasket, Stethoscope, type LucideIcon } from "lucide-react-native";
import type { LibraryFoodPanelItem } from "@/api/types";
import type { FoodPanelItem } from "@/components/panels";
import { tokens } from "@/design/tokens";

export const commitmentKinds: CalendarCommitmentKind[] = ["shopping", "cooking", "training", "nutritionist"];

export function commitmentSupportsFoods(kind: CalendarCommitmentKind): boolean {
  return kind === "shopping" || kind === "cooking";
}

export const commitmentPresentation: Record<CalendarCommitmentKind, { label: string; color: string; icon: LucideIcon }> = {
  shopping: { label: "Hacer compras", color: tokens.color.food, icon: ShoppingBasket },
  cooking: { label: "Cocinar", color: tokens.color.meal, icon: CookingPot },
  training: { label: "Entrenar", color: tokens.color.success, icon: Dumbbell },
  nutritionist: { label: "Cita nutricionista", color: tokens.color.interactivePrimary, icon: Stethoscope },
};

export const commitmentRegistrationTitle: Record<CalendarCommitmentKind, string> = {
  shopping: "Registrar días de compras",
  cooking: "Registrar días de cocinar",
  training: "Registrar días de entrenamiento",
  nutritionist: "Registrar citas con nutricionista",
};

export const commitmentDayTitle: Record<CalendarCommitmentKind, string> = {
  shopping: "Día de compras",
  cooking: "Día de cocinar",
  training: "Día de entrenamiento",
  nutritionist: "Cita nutricionista",
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
