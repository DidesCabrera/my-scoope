import assert from "node:assert/strict";
import test from "node:test";

import { createIdempotencyKey, pollJob } from "../src/ai_async_jobs.js";

function response(status, payload) {
  return { status, ok: status >= 200 && status < 300, async json() { return payload; } };
}

test("polls accepted states until the terminal payload", async () => {
  const responses = [
    response(202, { status: "queued", retry_after_ms: 10 }),
    response(202, { status: "running", retry_after_ms: 10 }),
    response(200, { thread_html: "<article>ok</article>" })
  ];
  const delays = [];
  const payload = await pollJob("/jobs/1/", {
    fetchImpl: async () => responses.shift(),
    delayImpl: async (milliseconds) => { delays.push(milliseconds); }
  });
  assert.equal(payload.thread_html, "<article>ok</article>");
  assert.deepEqual(delays, [500, 500]);
});

test("retries transient network failures with bounded backoff", async () => {
  let calls = 0;
  const delays = [];
  const payload = await pollJob("/jobs/2/", {
    fetchImpl: async () => {
      calls += 1;
      if (calls < 3) throw new TypeError("offline");
      return response(200, { status: "succeeded" });
    },
    delayImpl: async (milliseconds) => { delays.push(milliseconds); }
  });
  assert.equal(payload.status, "succeeded");
  assert.deepEqual(delays, [1000, 2000]);
});

test("does not retry a terminal server response", async () => {
  await assert.rejects(
    pollJob("/jobs/3/", {
      fetchImpl: async () => response(422, { error: "assistant_turn_failed" }),
      delayImpl: async () => {}
    }),
    (error) => error.code === "assistant_turn_failed" && error.status === 422
  );
});

test("prefers the platform UUID for idempotency", () => {
  assert.equal(createIdempotencyKey({ randomUUID: () => "stable-id" }), "stable-id");
});
