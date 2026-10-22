import * as Sentry from "@sentry/react-native";

import { normalizeDiagnosticPath } from "./sanitize";

export type NavigationReason = "disclosure_required" | "notification_open" | "onboarding_required" | "route_change";

export function recordNavigationTransition(from: string | null, to: string): void {
  const safeFrom = from ? normalizeDiagnosticPath(from) : "/launch";
  const safeTo = normalizeDiagnosticPath(to);
  Sentry.setTag("route", safeTo);
  Sentry.addBreadcrumb({
    category: "mobile.navigation",
    data: { from: safeFrom, reason: "route_change", to: safeTo },
    level: "info",
    message: "route_change",
    type: "navigation",
  });
}

export function recordNavigationRedirect(from: string, to: string, reason: Exclude<NavigationReason, "route_change">): void {
  Sentry.addBreadcrumb({
    category: "mobile.navigation",
    data: {
      from: normalizeDiagnosticPath(from),
      reason,
      to: normalizeDiagnosticPath(to),
    },
    level: "info",
    message: "route_change",
    type: "navigation",
  });
}
