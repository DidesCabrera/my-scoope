import * as Sentry from "@sentry/react-native";
import * as Application from "expo-application";

import { appConfig } from "@/config/app-config";

import { sanitizeSentryEvent, sanitizeSentryTransaction } from "./sanitize";

const dsn = process.env.EXPO_PUBLIC_SENTRY_DSN?.trim() ?? "";
const tracesSampleRate = Number(process.env.EXPO_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? "0.05");
const enabled = Boolean(dsn);

export const sentryNavigationIntegration = Sentry.reactNavigationIntegration({
  enableTimeToInitialDisplay: true,
  useDispatchedActionData: false,
  useFullPathsForNavigationRoutes: false,
});

Sentry.init({
  dsn,
  enabled,
  environment: appConfig.deploymentEnvironment,
  sendDefaultPii: false,
  attachScreenshot: false,
  attachViewHierarchy: false,
  integrations: [sentryNavigationIntegration],
  tracesSampleRate: Number.isFinite(tracesSampleRate) ? Math.min(Math.max(tracesSampleRate, 0), 1) : 0.05,
  enableAutoPerformanceTracing: enabled,
  enableAutoSessionTracking: enabled,
  beforeSend: sanitizeSentryEvent,
  beforeSendTransaction: sanitizeSentryTransaction,
});

Sentry.setTags({
  "app.build": Application.nativeBuildVersion ?? "development",
  "app.version": Application.nativeApplicationVersion ?? "development",
  "deployment.environment": appConfig.deploymentEnvironment,
});

export type WheelPickerKind = "date" | "height" | "portion" | "time" | "weight";
export type WheelPickerAction = "cancel" | "commit" | "open";
export type LibraryEditAction = "delete" | "finish" | "open" | "stale-reorder-dropped";

/** Record only the picker surface and lifecycle; selected values are deliberately excluded. */
export function recordWheelPickerInteraction(kind: WheelPickerKind, action: WheelPickerAction): void {
  Sentry.addBreadcrumb({
    category: "ui.wheel-picker",
    level: "info",
    message: `${kind}.${action}`,
  });
}

/** Record only the library kind, lifecycle action and item count; names and item IDs are excluded. */
export function recordLibraryEditInteraction(entity: "dailyPlan" | "food" | "meal" | "program", action: LibraryEditAction, itemCount: number): void {
  Sentry.addBreadcrumb({
    category: "ui.library-edit",
    data: { entity, item_count: Math.max(0, itemCount) },
    level: "info",
    message: action,
  });
}
