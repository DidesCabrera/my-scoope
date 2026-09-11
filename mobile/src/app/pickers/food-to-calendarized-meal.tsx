import { Redirect, useLocalSearchParams } from "expo-router";

import { CompositionPickerScreen } from "@/components/pickers/composition-picker-screen";

export default function FoodToCalendarizedMealPickerRoute() {
  const { dayId, mealKey } = useLocalSearchParams<{ dayId?: string; mealKey?: string }>();
  const targetId = Number(dayId);
  if (!Number.isInteger(targetId) || targetId <= 0 || !mealKey) return <Redirect href="/program" />;
  return <CompositionPickerScreen kind="food-to-calendarized-meal" mealKey={mealKey} targetId={targetId} />;
}
