import { Redirect, useLocalSearchParams } from "expo-router";

import { CompositionPickerScreen } from "@/components/pickers/composition-picker-screen";

export default function MealToCalendarizedDayPickerRoute() {
  const { dayId } = useLocalSearchParams<{ dayId?: string }>();
  const targetId = Number(dayId);
  if (!Number.isInteger(targetId) || targetId <= 0) return <Redirect href="/program" />;
  return <CompositionPickerScreen kind="meal-to-calendarized-day" targetId={targetId} />;
}
