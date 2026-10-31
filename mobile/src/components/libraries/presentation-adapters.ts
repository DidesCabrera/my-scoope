import type { FoodNutritionFacts } from "@/api/food-nutrition";
import type { LibraryNutrition } from "@/api/types";
import type { NutritionEntityCardProps } from "@/components/nutrition";
import type { NutritionFacts } from "@/components/ui";

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

export function libraryFoodNutritionFacts(macros: LibraryNutrition, facts?: FoodNutritionFacts | null): NutritionFacts {
  return {
    proteinG: macros.protein.grams,
    totalFatG: macros.fat.grams,
    saturatedFatG: facts?.saturated_fat_g ?? null,
    carbsG: macros.carbs.grams,
    sugarG: facts?.sugar_g ?? null,
    fiberG: facts?.fiber_g ?? null,
    sodiumMg: facts?.sodium_mg ?? null,
  };
}

export function libraryDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("es-CL", { day: "numeric", month: "short", year: "numeric" });
}
