import * as Sentry from "@sentry/react-native";

import type { MobileRequestMetric } from "@/auth/session-manager";

export function recordMobileRequestMetric(metric: MobileRequestMetric): void {
  Sentry.addBreadcrumb({
    category: "mobile-api.performance",
    level: metric.status >= 400 ? "warning" : "info",
    message: `${metric.method} ${metric.path}`,
    data: {
      cache: metric.cache,
      duration_ms: metric.durationMs,
      response_bytes: metric.responseBytes,
      status: metric.status,
    },
  });
}
