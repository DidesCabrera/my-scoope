import assert from "node:assert/strict";
import test from "node:test";

import {
  normalizeDiagnosticPath,
  routeTemplateFromSegments,
  sanitizeRequestId,
  sanitizeSentryEvent,
  sanitizeSentryTransaction,
} from "../src/observability/sanitize";

test("mobile crash events remove account and request payload data", () => {
  const event = sanitizeSentryEvent({
    user: { id: "private-user", email: "private@example.com" },
    extra: { rawLabelText: "private" },
    request: {
      cookies: "session=secret",
      data: { nutritionLabel: "private" },
      env: { TOKEN: "secret" },
      headers: { Authorization: "Bearer secret" },
      query_string: "email=private@example.com",
    },
    breadcrumbs: [{ category: "api", data: { body: "private" }, message: "request failed" }],
  });

  assert.equal(event.user, undefined);
  assert.equal(event.extra, undefined);
  assert.equal(event.request?.cookies, undefined);
  assert.equal(event.request?.data, undefined);
  assert.equal(event.request?.headers, undefined);
  assert.equal(event.breadcrumbs?.[0].message, undefined);
  assert.equal(event.breadcrumbs?.[0].data, undefined);
});

test("approved mobile diagnostics keep only normalized operational fields", () => {
  const event = sanitizeSentryEvent({
    breadcrumbs: [{
      category: "mobile-api.performance",
      data: {
        body: { private: true },
        cache: "network",
        duration_ms: 123.456,
        error_code: "mobile_api_error",
        method: "POST",
        outcome: "api_error",
        path: "/api/v1/program/days/42?email=private@example.com",
        request_id: "req-safe_123",
        response_bytes: 250,
        status: 500,
      },
      message: "POST /private/raw/path",
    }],
  });

  assert.deepEqual(event.breadcrumbs?.[0], {
    category: "mobile-api.performance",
    data: {
      cache: "network",
      duration_ms: 123.5,
      error_code: "mobile_api_error",
      method: "POST",
      outcome: "api_error",
      path: "/api/v1/program/days/:id",
      request_id: "req-safe_123",
      response_bytes: 250,
      status: 500,
    },
    level: undefined,
    message: "request_complete",
    timestamp: undefined,
    type: undefined,
  });
});

test("navigation diagnostics use file templates without route parameters", () => {
  assert.equal(routeTemplateFromSegments(["program", "days", "[id]", "meals", "[mealKey]"]), "/program/days/[id]/meals/[mealKey]");
  assert.equal(normalizeDiagnosticPath("https://www.myscoope.com/api/v1/program/days/42?token=secret"), "/api/v1/program/days/:id");
  assert.equal(sanitizeRequestId("req-safe_123"), "req-safe_123");
  assert.equal(sanitizeRequestId("private value with spaces"), null);
});

test("performance transactions remove payload data and normalize URLs", () => {
  const transaction = sanitizeSentryTransaction({
    extra: { private: true },
    request: { data: { private: true }, url: "https://www.myscoope.com/api/v1/library/foods/42?email=private@example.com" },
    spans: [{
      data: { requestBody: "private" },
      description: "GET https://www.myscoope.com/api/v1/library/foods/42?email=private@example.com",
      op: "http.client",
    }],
    transaction: "/program/days/42?private=true",
    user: { id: "private-user" },
  });

  assert.equal(transaction.user, undefined);
  assert.equal(transaction.extra, undefined);
  assert.equal(transaction.request?.data, undefined);
  assert.equal(transaction.request?.url, "/api/v1/library/foods/:id");
  assert.equal(transaction.transaction, "/program/days/:id");
  assert.equal(transaction.spans?.[0].data, undefined);
  assert.equal(transaction.spans?.[0].description, "GET /api/v1/library/foods/:id");
});
