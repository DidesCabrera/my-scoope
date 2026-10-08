import type { LibraryNutrition } from "@/api/types";

export function portionGrams(value: string): number {
  const grams = Number(value.trim().replace(",", "."));
  return Number.isFinite(grams) && grams > 0 ? grams : 0;
}

export function scaleFoodNutrition(nutrition: LibraryNutrition, quantity: string): LibraryNutrition {
  const grams = portionGrams(quantity);
  const factor = grams / 100;
  const hasPortion = grams > 0;

  return {
    calories: nutrition.calories * factor,
    protein: {
      ...nutrition.protein,
      allocation: hasPortion ? nutrition.protein.allocation : 0,
      grams: nutrition.protein.grams * factor,
    },
    carbs: {
      allocation: hasPortion ? nutrition.carbs.allocation : 0,
      grams: nutrition.carbs.grams * factor,
    },
    fat: {
      allocation: hasPortion ? nutrition.fat.allocation : 0,
      grams: nutrition.fat.grams * factor,
    },
  };
}
