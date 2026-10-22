import { useFocusEffect } from "expo-router";
import { useCallback } from "react";

import { CalendarOverviewScreen } from "@/components/calendarization/calendar-overview-screen";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";

export default function CalendarFutureScreen() {
  const setHeaderPresentation = useHeaderPresentation();
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/calendar", mode: "back", title: "Planes próximas fechas" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [setHeaderPresentation]));
  return <CalendarOverviewScreen extended />;
}
