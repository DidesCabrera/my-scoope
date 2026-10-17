import assert from "node:assert/strict";
import test from "node:test";
import { ForegroundRefresh } from "../src/billing/foreground-refresh";

const flush = () => new Promise((resolve) => setImmediate(resolve));
test("every background/active transition refreshes an idle subscription without navigation", async () => {
  let calls = 0;
  const foreground = new ForegroundRefresh({ refresh: async () => { calls += 1; }, retry: () => false }, "active");
  await foreground.refresh();
  foreground.transition("background");
  foreground.transition("active");
  await flush();
  assert.equal(calls, 2);
  foreground.transition("active");
  await flush();
  assert.equal(calls, 2);
  foreground.dispose();
});
test("focus and reconnect coalesce, but a resume during an old read requests one fresh follow-up", async () => {
  let release!: () => void;
  let calls = 0;
  const foreground = new ForegroundRefresh({ refresh: async () => { if (++calls === 1) await new Promise<void>((resolve) => { release = resolve; }); }, retry: () => false }, "active");
  const first = foreground.refresh();
  assert.equal(first, foreground.refresh());
  foreground.transition("inactive");
  foreground.transition("active");
  assert.equal(first, foreground.refresh());
  release();
  await first;
  assert.equal(calls, 2);
  foreground.dispose();
});
test("offline failures retain known state, retry while active and update immediately on recovery", async () => {
  let offline = true;
  let plan = "Pro";
  let credits = 3488;
  let scheduled: (() => void) | null = null;
  let cancelled = 0;
  const foreground = new ForegroundRefresh({
    refresh: async () => { if (offline) throw new TypeError("fetch failed"); plan = "Free"; credits = 3000; },
    retry: () => true,
    schedule: (run, delay) => { assert.ok([3000, 6000].includes(delay)); scheduled = run; return () => { cancelled += 1; scheduled = null; }; },
  }, "active");
  await assert.rejects(foreground.refresh());
  assert.equal(plan, "Pro");
  assert.equal(credits, 3488);
  foreground.transition("background");
  assert.equal(scheduled, null);
  assert.equal(cancelled, 1);
  foreground.transition("active");
  await flush();
  assert.ok(scheduled);
  offline = false;
  (scheduled as () => void)();
  await flush();
  assert.equal(plan, "Free");
  assert.equal(credits, 3000);
  foreground.dispose();
});
test("an account disposed offline cannot schedule or apply another retry", async () => {
  let release!: () => void;
  let scheduled = false;
  const foreground = new ForegroundRefresh({
    refresh: async () => { await new Promise<void>((resolve) => { release = resolve; }); throw new Error("offline"); },
    retry: () => true, schedule: () => { scheduled = true; return () => undefined; },
  }, "active");
  const task = foreground.refresh();
  foreground.dispose();
  release();
  await assert.rejects(task);
  assert.equal(scheduled, false);
});
