import assert from "node:assert/strict";
import test from "node:test";

import { createCalendarMonthCache } from "../src/components/calendarization/calendar-month-cache";

test("calendar month cache reuses loaded months and prefetches adjacent months", async () => {
  const requests: string[] = [];
  const cache = createCalendarMonthCache(async <T>(path: string) => {
    requests.push(path);
    return { days: [], end_date: "2026-10-31", local_date: "2026-10-24", start_date: "2026-10-01" } as T;
  });

  const first = await cache.load("2026-10");
  const second = await cache.load("2026-10");
  assert.strictEqual(first, second);
  assert.equal(requests.length, 1);

  cache.prefetchAdjacent("2026-10");
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(requests.length, 3);
  assert.ok(cache.get("2026-09"));
  assert.ok(cache.get("2026-11"));

  cache.invalidate(["2026-10"]);
  assert.equal(cache.get("2026-10"), undefined);
});
