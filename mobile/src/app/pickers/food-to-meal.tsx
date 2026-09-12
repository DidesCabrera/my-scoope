import { Redirect, useLocalSearchParams } from "expo-router";

import { CompositionPickerScreen } from "@/components/pickers/composition-picker-screen";
import { internalHref } from "@/navigation/internal-href";

export default function FoodToMealPickerRoute() {
  const { dailyPlanId, dailyPlanMealId, mealFoodId, mealId, returnTo } = useLocalSearchParams<{ dailyPlanId?: string; dailyPlanMealId?: string; mealFoodId?: string; mealId?: string; returnTo?: string }>();
  const targetId = Number(mealId);
  const relationId = Number(mealFoodId) || undefined;
  if (!Number.isInteger(targetId) || targetId <= 0) return <Redirect href="/libraries/meals" />;
  return <CompositionPickerScreen contextDailyPlanId={Number(dailyPlanId) || undefined} contextDailyPlanMealId={Number(dailyPlanMealId) || undefined} kind="food-to-meal" relationId={relationId} returnTo={internalHref(returnTo)} targetId={targetId} />;
}
