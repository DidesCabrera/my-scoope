import * as Sentry from "@sentry/react-native";

import type { MobileRequestMetric } from "@/auth/session-manager";
import { normalizeDiagnosticPath, sanitizeRequestId } from "@/observability/sanitize";

export function recordMobileRequestMetric(metric: MobileRequestMetric): void {
  const errorCode = metric.errorCode && /^[a-z0-9_]{1,80}$/.test(metric.errorCode) ? metric.errorCode : null;
  const method = /^(DELETE|GET|HEAD|OPTIONS|PATCH|POST|PUT)$/.test(metric.method) ? metric.method : "GET";
  const path = normalizeDiagnosticPath(metric.path);
  const requestId = sanitizeRequestId(metric.requestId);
  Sentry.addBreadcrumb({
    category: "mobile-api.performance",
    level: metric.outcome === "success" ? "info" : "warning",
    message: "request_complete",
    data: {
      cache: metric.cache,
      duration_ms: metric.durationMs,
      error_code: errorCode,
      method,
      outcome: metric.outcome,
      path,
      request_id: requestId,
      response_bytes: metric.responseBytes,
      status: metric.status,
    },
  });

  if (metric.status < 500 && metric.outcome !== "invalid_response") return;
  Sentry.captureMessage(
    metric.outcome === "invalid_response" ? "Mobile API contract failure" : "Mobile API server failure",
    {
      fingerprint: ["mobile-api", metric.outcome, method, path],
      level: "error",
      tags: {
        "mobile.api.error_code": errorCode ?? "none",
        "mobile.api.method": method,
        "mobile.api.outcome": metric.outcome,
        "mobile.api.path": path,
        "mobile.api.request_id": requestId ?? "unavailable",
        "mobile.api.status": String(metric.status),
      },
    },
  );
}
