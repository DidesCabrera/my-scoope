import { Redirect, useLocalSearchParams } from "expo-router";

import { CompositionPickerScreen } from "@/components/pickers/composition-picker-screen";

export default function MealToDailyPlanPickerRoute() {
  const { dailyPlanId, dailyPlanMealId } = useLocalSearchParams<{ dailyPlanId?: string; dailyPlanMealId?: string }>();
  const targetId = Number(dailyPlanId);
  const relationId = Number(dailyPlanMealId) || undefined;
  if (!Number.isInteger(targetId) || targetId <= 0) return <Redirect href="/libraries/daily-plans" />;
  return <CompositionPickerScreen kind="meal-to-dailyplan" relationId={relationId} targetId={targetId} />;
}
