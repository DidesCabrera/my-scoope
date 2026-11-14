import type { PreparationDetail } from "@/api/preparations";

export function preparationNutritionForGrams(detail: PreparationDetail, grams: number): PreparationDetail["nutrition"] {
  const factor = grams / detail.yield_g;
  const nutrition = detail.nutrition;
  return {
    ...nutrition,
    calories: nutrition.calories * factor,
    protein_g: nutrition.protein_g * factor,
    protein_per_kilogram: nutrition.protein_per_kilogram == null ? null : nutrition.protein_per_kilogram * factor,
    carbs_g: nutrition.carbs_g * factor,
    fat_g: nutrition.fat_g * factor,
    sodium_mg: nutrition.sodium_mg == null ? null : nutrition.sodium_mg * factor,
  };
}
