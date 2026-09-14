import type { ShareResource } from "@/api/types";
import type { FoodPanelItem, MealPanelItem } from "@/components/panels";

export type ShareNutrition = NonNullable<ShareResource["snapshot"]>["nutrition"];
export type ShareMeal = NonNullable<NonNullable<ShareResource["snapshot"]>["meals"]>[number];

export function sharedNutrition(values: ShareNutrition) {
  const calories = values.calories || values.protein_grams * 4 + values.carbs_grams * 4 + values.fat_grams * 9;
  return {
    calories,
    protein: { grams: values.protein_grams, allocation: calories > 0 ? values.protein_grams * 4 * 100 / calories : 0 },
    carbs: { grams: values.carbs_grams, allocation: calories > 0 ? values.carbs_grams * 4 * 100 / calories : 0 },
    fat: { grams: values.fat_grams, allocation: calories > 0 ? values.fat_grams * 9 * 100 / calories : 0 },
  };
}

export function sharedFoodPanelItems(meal: ShareMeal): FoodPanelItem[] {
  return meal.foods.map((food, index) => {
    const item = sharedNutrition(food.nutrition);
    return {
      id: `shared-food-${index}`,
      name: food.name,
      quantity: food.quantity_grams,
      quantityUnit: "g",
      calories: item.calories,
      calorieShare: meal.nutrition.calories > 0 ? item.calories * 100 / meal.nutrition.calories : 0,
      proteinGrams: item.protein.grams,
      carbsGrams: item.carbs.grams,
      fatGrams: item.fat.grams,
      proteinAllocation: item.protein.allocation,
      carbsAllocation: item.carbs.allocation,
      fatAllocation: item.fat.allocation,
    };
  });
}

export function sharedMealPanelItems(meals: ShareMeal[], planCalories: number): MealPanelItem[] {
  return meals.map((meal, index) => {
    const item = sharedNutrition(meal.nutrition);
    return {
      canOpen: true,
      id: String(index),
      name: meal.name,
      time: meal.time?.slice(0, 5) ?? undefined,
      foods: meal.foods.map((food) => ({ name: food.name, quantity: food.quantity_grams, quantityUnit: "g" })),
      calories: item.calories,
      calorieShare: planCalories > 0 ? item.calories * 100 / planCalories : 0,
      proteinGrams: item.protein.grams,
      carbsGrams: item.carbs.grams,
      fatGrams: item.fat.grams,
      proteinAllocation: item.protein.allocation,
      carbsAllocation: item.carbs.allocation,
      fatAllocation: item.fat.allocation,
    };
  });
}
