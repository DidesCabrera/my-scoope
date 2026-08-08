import * as Sentry from "@sentry/react-native";

import { sanitizeSentryEvent } from "./sanitize";

const dsn = process.env.EXPO_PUBLIC_SENTRY_DSN?.trim() ?? "";

Sentry.init({
  dsn,
  enabled: Boolean(dsn),
  sendDefaultPii: false,
  attachScreenshot: false,
  attachViewHierarchy: false,
  tracesSampleRate: 0,
  enableAutoSessionTracking: false,
  beforeSend: sanitizeSentryEvent,
});
