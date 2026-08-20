import type { LibraryNutrition } from "@/api/types";
import type { NutritionEntityCardProps } from "@/components/nutrition";

export function libraryNutrition(nutrition: LibraryNutrition): NutritionEntityCardProps["nutrition"] {
  return {
    calories: nutrition.calories,
    protein: {
      ...nutrition.protein,
      perKilogram: nutrition.protein.per_kilogram,
    },
    carbs: nutrition.carbs,
    fat: nutrition.fat,
  };
}

export function libraryDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("es-CL", { day: "numeric", month: "short", year: "numeric" });
}
