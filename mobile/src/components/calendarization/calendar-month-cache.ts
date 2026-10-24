import type { CalendarOverviewData } from "@/api/calendar-types";
import { monthWindow, shiftMonth } from "@/components/calendarization/calendar-month";

type CalendarRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

export function createCalendarMonthCache(apiRequest: CalendarRequest) {
  const cached = new Map<string, CalendarOverviewData>();
  const pending = new Map<string, Promise<CalendarOverviewData>>();

  function get(month: string): CalendarOverviewData | undefined {
    return cached.get(month);
  }

  function load(month: string): Promise<CalendarOverviewData> {
    const existing = cached.get(month);
    if (existing) return Promise.resolve(existing);
    const inFlight = pending.get(month);
    if (inFlight) return inFlight;
    const window = monthWindow(month);
    const request = apiRequest<CalendarOverviewData>(`/api/v1/calendar?start_date=${window.startDate}&days=${window.days}`)
      .then((data) => { cached.set(month, data); return data; })
      .finally(() => pending.delete(month));
    pending.set(month, request);
    return request;
  }

  function prefetchAdjacent(month: string): void {
    void load(shiftMonth(month, -1)).catch(() => undefined);
    void load(shiftMonth(month, 1)).catch(() => undefined);
  }

  function invalidate(months: Iterable<string>): void {
    for (const month of months) cached.delete(month);
  }

  return { get, invalidate, load, prefetchAdjacent };
}
