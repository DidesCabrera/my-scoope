import { Redirect, useLocalSearchParams } from "expo-router";

import { CompositionPickerScreen } from "@/components/pickers/composition-picker-screen";

export default function FoodToMealPickerRoute() {
  const { mealId } = useLocalSearchParams<{ mealId?: string }>();
  const targetId = Number(mealId);
  if (!Number.isInteger(targetId) || targetId <= 0) return <Redirect href="/libraries/meals" />;
  return <CompositionPickerScreen kind="food-to-meal" targetId={targetId} />;
}
