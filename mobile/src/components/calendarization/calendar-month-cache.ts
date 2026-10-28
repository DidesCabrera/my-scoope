import type { CalendarOverviewData } from "@/api/calendar-types";
import { monthWindow } from "@/components/calendarization/calendar-month";

type CalendarRequest = <T>(path: string, init?: RequestInit) => Promise<T>;
type CachedMonth = { data: CalendarOverviewData; storedAt: number; revision: number };

const MONTH_TTL_MS = 30_000;
const MAX_MONTHS = 6;
const caches = new WeakMap<CalendarRequest, ReturnType<typeof buildCalendarMonthCache>>();
let revision = 0;

export function invalidateCalendarMonthCaches(): void {
  revision += 1;
}

function buildCalendarMonthCache(apiRequest: CalendarRequest, now: () => number) {
  const cached = new Map<string, CachedMonth>();
  const pending = new Map<string, { request: Promise<CalendarOverviewData>; revision: number }>();
  let cacheRevision = revision;

  function discardStaleRevision(): void {
    if (cacheRevision === revision) return;
    cached.clear();
    pending.clear();
    cacheRevision = revision;
  }

  function get(month: string): CalendarOverviewData | undefined {
    discardStaleRevision();
    const entry = cached.get(month);
    if (!entry) return undefined;
    if (entry.revision === revision && now() - entry.storedAt < MONTH_TTL_MS) return entry.data;
    cached.delete(month);
    return undefined;
  }

  function load(month: string): Promise<CalendarOverviewData> {
    discardStaleRevision();
    const existing = get(month);
    if (existing) return Promise.resolve(existing);
    const inFlight = pending.get(month);
    if (inFlight?.revision === revision) return inFlight.request;
    const window = monthWindow(month);
    const requestRevision = revision;
    const request = apiRequest<CalendarOverviewData>(`/api/v1/calendar?start_date=${window.startDate}&days=${window.days}`)
      .then((data) => {
        if (requestRevision !== revision) return load(month);
        if (!cached.has(month) && cached.size >= MAX_MONTHS) {
          const oldest = cached.keys().next().value;
          if (oldest) cached.delete(oldest);
        }
        cached.set(month, { data, revision, storedAt: now() });
        return data;
      })
      .finally(() => {
        if (pending.get(month)?.request === request) pending.delete(month);
      });
    pending.set(month, { request, revision: requestRevision });
    return request;
  }

  function invalidate(months: Iterable<string>): void {
    for (const month of months) cached.delete(month);
  }

  return { get, invalidate, load };
}

export function createCalendarMonthCache(apiRequest: CalendarRequest, now: () => number = Date.now) {
  const existing = caches.get(apiRequest);
  if (existing) return existing;
  const cache = buildCalendarMonthCache(apiRequest, now);
  caches.set(apiRequest, cache);
  return cache;
}
