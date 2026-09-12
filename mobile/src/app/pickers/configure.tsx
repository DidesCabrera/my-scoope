import { Redirect, Stack, useLocalSearchParams } from "expo-router";

import { CompositionPickerScreen, type PickerKind } from "@/components/pickers/composition-picker-screen";
import { internalHref } from "@/navigation/internal-href";

const pickerKinds = new Set<PickerKind>(["food-to-meal", "meal-to-dailyplan", "dailyplan-to-program", "dailyplan-to-calendarized-day", "meal-to-calendarized-day", "food-to-calendarized-meal"]);

export default function ConfigureCompositionPickerRoute() {
  const { contextDailyPlanId, contextDailyPlanMealId, dayNumber, kind, mealKey, relationId, returnTo, selectedId, targetId, weekNumber } = useLocalSearchParams<{
    contextDailyPlanId?: string;
    contextDailyPlanMealId?: string;
    dayNumber?: string;
    kind?: string;
    mealKey?: string;
    relationId?: string;
    returnTo?: string;
    selectedId?: string;
    targetId?: string;
    weekNumber?: string;
  }>();
  const pickerKind = kind && pickerKinds.has(kind as PickerKind) ? kind as PickerKind : null;
  const target = Number(targetId);
  const selection = Number(selectedId);
  const week = Number(weekNumber) || 1;
  const day = Number(dayNumber) || undefined;
  const relation = Number(relationId) || undefined;
  const returnHref = internalHref(returnTo);

  if (!pickerKind || !Number.isInteger(target) || target <= 0 || !Number.isInteger(selection) || selection <= 0) {
    return <Redirect href="/today" />;
  }
  return (
    <>
      <Stack.Screen options={{ animation: "slide_from_right" }} />
      <CompositionPickerScreen
        contextDailyPlanId={Number(contextDailyPlanId) || undefined}
        contextDailyPlanMealId={Number(contextDailyPlanMealId) || undefined}
        initialDayNumber={day}
        kind={pickerKind}
        mealKey={mealKey}
        relationId={relation}
        returnTo={returnHref}
        selectedId={selection}
        targetId={target}
        weekNumber={week}
      />
    </>
  );
}
