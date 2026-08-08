import assert from "node:assert/strict";
import test from "node:test";

import { sanitizeSentryEvent } from "../src/observability/sanitize";

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
