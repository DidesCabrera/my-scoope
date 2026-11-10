import type { LibraryFoodPanelItem, LibraryNutrition, LibraryPanel } from "@/api/types";

function percentage(part: number, total: number): number {
  return total > 0 ? part / total * 100 : 0;
}

/** Library list cards omit panel.foods; their meal rows still contain the food data. */
export function dailyPlanFoodPanelItems(panel: LibraryPanel, nutrition: LibraryNutrition): LibraryFoodPanelItem[] {
  if (panel.foods.length > 0) return panel.foods;

  const foods = new Map<string, LibraryFoodPanelItem>();
  for (const meal of panel.meals) {
    for (const food of meal.foods) {
      const key = food.detail_id != null
        ? `${food.detail_id}:${food.quantity_unit}`
        : `${food.name.trim().toLocaleLowerCase()}:${food.quantity_unit}`;
      const previous = foods.get(key);
      if (!previous) {
        foods.set(key, {
          ...food,
          id: `daily-plan-food:${key}`,
          relation_id: null,
          calorie_share: 0,
          protein_allocation: 0,
          carbs_allocation: 0,
          fat_allocation: 0,
        });
      } else {
        const samePortionMeasure = previous.portion_display_measure === food.portion_display_measure;
        foods.set(key, {
          ...previous,
          quantity: previous.quantity + food.quantity,
          calories: previous.calories + food.calories,
          protein_grams: previous.protein_grams + food.protein_grams,
          carbs_grams: previous.carbs_grams + food.carbs_grams,
          fat_grams: previous.fat_grams + food.fat_grams,
          portion_display_quantity: samePortionMeasure
            && previous.portion_display_quantity != null && food.portion_display_quantity != null
            ? previous.portion_display_quantity + food.portion_display_quantity : null,
          portion_display_measure: samePortionMeasure ? previous.portion_display_measure : null,
        });
      }
    }
  }

  return [...foods.values()].map((food) => {
    const macroCalories = food.protein_grams * 4 + food.carbs_grams * 4 + food.fat_grams * 9;
    return {
    ...food,
    calorie_share: percentage(food.calories, nutrition.calories),
    protein_per_kilogram: nutrition.protein.grams > 0 && nutrition.protein.per_kilogram != null
      ? food.protein_grams * nutrition.protein.per_kilogram / nutrition.protein.grams : null,
    protein_allocation: percentage(food.protein_grams, nutrition.protein.grams),
    carbs_allocation: percentage(food.carbs_grams, nutrition.carbs.grams),
    fat_allocation: percentage(food.fat_grams, nutrition.fat.grams),
    calorie_distribution: {
      protein: percentage(food.protein_grams * 4, macroCalories),
      carbs: percentage(food.carbs_grams * 4, macroCalories),
      fat: percentage(food.fat_grams * 9, macroCalories),
    },
    };
  });
}
