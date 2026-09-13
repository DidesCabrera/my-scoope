import { Redirect, useLocalSearchParams } from "expo-router";

import { CompositionPickerScreen } from "@/components/pickers/composition-picker-screen";
import { internalHref } from "@/navigation/internal-href";

export default function MealToCalendarizedDayPickerRoute() {
  const { dayId, relationKey, returnTo } = useLocalSearchParams<{ dayId?: string; relationKey?: string; returnTo?: string }>();
  const targetId = Number(dayId);
  if (!Number.isInteger(targetId) || targetId <= 0) return <Redirect href="/program" />;
  return <CompositionPickerScreen kind="meal-to-calendarized-day" relationKey={relationKey} returnTo={internalHref(returnTo)} targetId={targetId} />;
}
