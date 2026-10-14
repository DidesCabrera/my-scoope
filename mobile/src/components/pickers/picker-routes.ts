import type { Href } from "expo-router";

export type PickerKind =
  | "food-to-meal"
  | "meal-to-dailyplan"
  | "dailyplan-to-program"
  | "dailyplan-to-calendarized-day"
  | "meal-to-calendarized-day"
  | "food-to-calendarized-meal";

export function pickerHref(kind: PickerKind, params: Record<string, string | number>): Href {
  const query = new URLSearchParams(Object.entries(params).map(([key, value]) => [key, String(value)])).toString();
  return `/pickers/${kind}?${query}` as Href;
}

export function pickerConfigureHref(
  kind: PickerKind,
  { contextDailyPlanId, contextDailyPlanMealId, dayNumber, mealKey, relationId, relationKey, returnTo, selectedId, targetId, weekNumber }: { contextDailyPlanId?: number; contextDailyPlanMealId?: number; dayNumber?: number; mealKey?: string; relationId?: number; relationKey?: string; returnTo?: Href; selectedId: number; targetId: number; weekNumber: number },
): Href {
  const params: Record<string, string> = {
    kind,
    selectedId: String(selectedId),
    targetId: String(targetId),
    weekNumber: String(weekNumber),
  };
  if (dayNumber) params.dayNumber = String(dayNumber);
  if (mealKey) params.mealKey = mealKey;
  if (relationId) params.relationId = String(relationId);
  if (relationKey) params.relationKey = relationKey;
  if (contextDailyPlanId) params.contextDailyPlanId = String(contextDailyPlanId);
  if (contextDailyPlanMealId) params.contextDailyPlanMealId = String(contextDailyPlanMealId);
  if (returnTo) params.returnTo = String(returnTo);
  return { pathname: "/pickers/configure", params } as Href;
}
