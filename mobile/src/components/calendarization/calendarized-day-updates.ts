import type { CalendarizedDayDetail } from "@/api/types";

type CalendarizedDayUpdateListener = (day: CalendarizedDayDetail) => void;

const listeners = new Set<CalendarizedDayUpdateListener>();

export function publishCalendarizedDayUpdate(day: CalendarizedDayDetail): void {
  for (const listener of listeners) listener(day);
}

export function subscribeToCalendarizedDayUpdates(listener: CalendarizedDayUpdateListener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
