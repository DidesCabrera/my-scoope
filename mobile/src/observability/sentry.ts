import * as Sentry from "@sentry/react-native";

import { sanitizeSentryEvent } from "./sanitize";

const dsn = process.env.EXPO_PUBLIC_SENTRY_DSN?.trim() ?? "";
const tracesSampleRate = Number(process.env.EXPO_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? "0.05");

Sentry.init({
  dsn,
  enabled: Boolean(dsn),
  sendDefaultPii: false,
  attachScreenshot: false,
  attachViewHierarchy: false,
  tracesSampleRate: Number.isFinite(tracesSampleRate) ? Math.min(Math.max(tracesSampleRate, 0), 1) : 0.05,
  enableAutoSessionTracking: false,
  beforeSend: sanitizeSentryEvent,
});
