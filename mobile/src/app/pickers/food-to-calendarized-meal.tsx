import { Redirect, useLocalSearchParams } from "expo-router";

import { CompositionPickerScreen } from "@/components/pickers/composition-picker-screen";
import { internalHref } from "@/navigation/internal-href";

export default function FoodToCalendarizedMealPickerRoute() {
  const { dayId, mealKey, relationKey, returnTo } = useLocalSearchParams<{ dayId?: string; mealKey?: string; relationKey?: string; returnTo?: string }>();
  const targetId = Number(dayId);
  if (!Number.isInteger(targetId) || targetId <= 0 || !mealKey) return <Redirect href="/program" />;
  return <CompositionPickerScreen kind="food-to-calendarized-meal" mealKey={mealKey} relationKey={relationKey} returnTo={internalHref(returnTo)} targetId={targetId} />;
}
