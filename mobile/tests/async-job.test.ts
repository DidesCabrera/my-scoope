import assert from "node:assert/strict";
import test from "node:test";

import { AsyncJobProtocolError, AsyncJobTimeoutError, pollAsyncJob } from "../src/api/async-job";

test("polls the durable job using the server retry delay until a result is ready", async () => {
  const snapshots = [
    { job_id: "job-1", status: "queued" as const, retry_after_ms: 325, result: null },
    { job_id: "job-1", status: "running" as const, retry_after_ms: 900, result: null },
    { job_id: "job-1", status: "succeeded" as const, retry_after_ms: null, result: { chat_id: 14 } },
  ];
  const delays: number[] = [];
  const result = await pollAsyncJob({
    path: "/api/v1/ai/jobs/job-1",
    request: async () => snapshots.shift()!,
    wait: async (delay) => { delays.push(delay); },
  });

  assert.deepEqual(result, { chat_id: 14 });
  assert.deepEqual(delays, [325, 900]);
});

test("fails closed when a succeeded job omits its typed result", async () => {
  await assert.rejects(
    pollAsyncJob({
      path: "/api/v1/ai/jobs/job-2",
      request: async () => ({ job_id: "job-2", status: "succeeded", retry_after_ms: null, result: null }),
    }),
    AsyncJobProtocolError,
  );
});

test("bounds polling instead of waiting forever", async () => {
  let polls = 0;
  await assert.rejects(
    pollAsyncJob({
      path: "/api/v1/ai/jobs/job-3",
      maxPolls: 2,
      request: async () => {
        polls += 1;
        return { job_id: "job-3", status: "running" as const, retry_after_ms: 0, result: null };
      },
      wait: async () => undefined,
    }),
    AsyncJobTimeoutError,
  );
  assert.equal(polls, 2);
});

test("honors cancellation before making a network request", async () => {
  const controller = new AbortController();
  controller.abort();
  let requested = false;
  await assert.rejects(
    pollAsyncJob({
      path: "/api/v1/ai/jobs/job-4",
      request: async () => {
        requested = true;
        return { job_id: "job-4", status: "running" as const, retry_after_ms: 0, result: null };
      },
      signal: controller.signal,
    }),
    (error: unknown) => error instanceof Error && error.name === "AbortError",
  );
  assert.equal(requested, false);
});
