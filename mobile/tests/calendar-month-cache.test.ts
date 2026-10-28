import assert from "node:assert/strict";
import test from "node:test";

import { createCalendarMonthCache, invalidateCalendarMonthCaches } from "../src/components/calendarization/calendar-month-cache";

test("calendar month cache is shared, bounded in time, and loads only the requested month", async () => {
  const requests: string[] = [];
  let now = 1_000;
  const apiRequest = async <T>(path: string) => {
    requests.push(path);
    return { days: [], end_date: "2026-10-31", local_date: "2026-10-24", start_date: "2026-10-01" } as T;
  };
  const firstScreen = createCalendarMonthCache(apiRequest, () => now);
  const secondScreen = createCalendarMonthCache(apiRequest);

  const first = await firstScreen.load("2026-10");
  assert.strictEqual(await secondScreen.load("2026-10"), first);
  assert.equal(requests.length, 1);

  now += 30_001;
  await firstScreen.load("2026-10");
  assert.equal(requests.length, 2);

  invalidateCalendarMonthCaches();
  assert.equal(secondScreen.get("2026-10"), undefined);
  await secondScreen.load("2026-10");
  assert.equal(requests.length, 3);
});

test("an invalidated in-flight month read cannot refill the cache with stale data", async () => {
  let release!: (value: { days: []; end_date: string; local_date: string; start_date: string }) => void;
  let calls = 0;
  const apiRequest = async <T>() => {
    calls += 1;
    if (calls === 1) return new Promise<T>((resolve) => { release = resolve as typeof release; });
    return { days: [], end_date: "2026-10-31", local_date: "2026-10-27", start_date: "2026-10-01" } as T;
  };
  const cache = createCalendarMonthCache(apiRequest);
  const oldRead = cache.load("2026-10");
  invalidateCalendarMonthCaches();
  const freshRead = cache.load("2026-10");
  release({ days: [], end_date: "2026-10-31", local_date: "2026-10-24", start_date: "2026-10-01" });

  assert.equal((await oldRead).local_date, "2026-10-27");
  assert.equal((await freshRead).local_date, "2026-10-27");
  assert.equal(cache.get("2026-10")?.local_date, "2026-10-27");
  assert.equal(calls, 2);
});
