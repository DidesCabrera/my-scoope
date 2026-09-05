import { type Href, Redirect, Stack, useLocalSearchParams } from "expo-router";

import { CompositionPickerScreen, type PickerKind } from "@/components/pickers/composition-picker-screen";

const pickerKinds = new Set<PickerKind>(["food-to-meal", "meal-to-dailyplan", "dailyplan-to-program"]);

export default function ConfigureCompositionPickerRoute() {
  const { contextDailyPlanId, contextDailyPlanMealId, dayNumber, kind, relationId, returnTo, selectedId, targetId, weekNumber } = useLocalSearchParams<{
    contextDailyPlanId?: string;
    contextDailyPlanMealId?: string;
    dayNumber?: string;
    kind?: string;
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
  const returnHref = typeof returnTo === "string" && returnTo.startsWith("/pickers/week-to-program?") ? returnTo as Href : undefined;

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
        relationId={relation}
        returnTo={returnHref}
        selectedId={selection}
        targetId={target}
        weekNumber={week}
      />
    </>
  );
}
