import { Redirect, useLocalSearchParams } from "expo-router";

import { CompositionPickerScreen } from "@/components/pickers/composition-picker-screen";
import { internalHref } from "@/navigation/internal-href";

export default function MealToCalendarizedDayPickerRoute() {
  const { dayId, returnTo } = useLocalSearchParams<{ dayId?: string; returnTo?: string }>();
  const targetId = Number(dayId);
  if (!Number.isInteger(targetId) || targetId <= 0) return <Redirect href="/program" />;
  return <CompositionPickerScreen kind="meal-to-calendarized-day" returnTo={internalHref(returnTo)} targetId={targetId} />;
}
