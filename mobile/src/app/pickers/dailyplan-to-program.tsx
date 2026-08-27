import { type Href, Redirect, useLocalSearchParams } from "expo-router";

import { CompositionPickerScreen } from "@/components/pickers/composition-picker-screen";

export default function DailyPlanToProgramPickerRoute() {
  const { programId, weekNumber, dayNumber, returnTo } = useLocalSearchParams<{ programId?: string; weekNumber?: string; dayNumber?: string; returnTo?: string }>();
  const targetId = Number(programId);
  const week = Number(weekNumber) || 1;
  const day = Number(dayNumber) || undefined;
  const returnHref = typeof returnTo === "string" && returnTo.startsWith("/pickers/week-to-program?") ? returnTo as Href : undefined;
  if (!Number.isInteger(targetId) || targetId <= 0) return <Redirect href="/libraries/programs" />;
  return <CompositionPickerScreen initialDayNumber={day} kind="dailyplan-to-program" returnTo={returnHref} targetId={targetId} weekNumber={week} />;
}
