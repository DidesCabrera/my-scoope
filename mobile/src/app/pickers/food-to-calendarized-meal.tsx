import { Redirect, useLocalSearchParams } from "expo-router";

import { CompositionPickerScreen } from "@/components/pickers/composition-picker-screen";

export default function FoodToCalendarizedMealPickerRoute() {
  const { dayId, mealKey, relationKey } = useLocalSearchParams<{ dayId?: string; mealKey?: string; relationKey?: string }>();
  const targetId = Number(dayId);
  if (!Number.isInteger(targetId) || targetId <= 0 || !mealKey) return <Redirect href="/program" />;
  return <CompositionPickerScreen kind="food-to-calendarized-meal" mealKey={mealKey} relationKey={relationKey} targetId={targetId} />;
}
