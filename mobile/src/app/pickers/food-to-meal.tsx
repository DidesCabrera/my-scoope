import { Redirect, useLocalSearchParams } from "expo-router";

import { CompositionPickerScreen } from "@/components/pickers/composition-picker-screen";

export default function FoodToMealPickerRoute() {
  const { mealFoodId, mealId } = useLocalSearchParams<{ mealFoodId?: string; mealId?: string }>();
  const targetId = Number(mealId);
  const relationId = Number(mealFoodId) || undefined;
  if (!Number.isInteger(targetId) || targetId <= 0) return <Redirect href="/libraries/meals" />;
  return <CompositionPickerScreen kind="food-to-meal" relationId={relationId} targetId={targetId} />;
}
