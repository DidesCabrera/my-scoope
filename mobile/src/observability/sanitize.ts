type BreadcrumbData = Record<string, unknown>;

export type SanitizableEvent = {
  user?: unknown;
  extra?: unknown;
  transaction?: string;
  request?: {
    cookies?: unknown;
    data?: unknown;
    env?: unknown;
    headers?: unknown;
    query_string?: unknown;
    url?: unknown;
  };
  breadcrumbs?: {
    category?: string;
    data?: unknown;
    level?: string;
    message?: string;
    timestamp?: number;
    type?: string;
  }[];
};

export type SanitizableTransaction = SanitizableEvent & {
  spans?: {
    data?: unknown;
    description?: string;
    op?: string;
  }[];
};

const REQUEST_ID_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const HTTP_METHOD_PATTERN = /^(DELETE|GET|HEAD|OPTIONS|PATCH|POST|PUT)$/;
const NAVIGATION_REASON_PATTERN = /^(disclosure_required|notification_open|onboarding_required|route_change)$/;

export function normalizeDiagnosticPath(value: unknown): string {
  if (typeof value !== "string") return "/unknown";
  const trimmed = value.trim();
  if (!trimmed) return "/unknown";
  const withoutOrigin = trimmed.replace(/^https?:\/\/[^/]+/i, "");
  const pathname = (withoutOrigin.split(/[?#]/, 1)[0] || "/").slice(0, 240);
  const rooted = pathname.startsWith("/") ? pathname : `/${pathname}`;
  return rooted.replace(
    /\/(?:\d+|[0-9a-f]{8}-[0-9a-f-]{27,}|[A-Za-z0-9_-]{20,})(?=\/|$)/gi,
    "/:id",
  );
}

export function routeTemplateFromSegments(segments: readonly string[]): string {
  if (segments.length === 0) return "/";
  const safeSegments = segments
    .slice(0, 12)
    .map((segment) => /^[A-Za-z0-9_+().\-[\]]{1,80}$/.test(segment) ? segment : "[filtered]");
  return `/${safeSegments.join("/")}`;
}

export function sanitizeRequestId(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return REQUEST_ID_PATTERN.test(trimmed) ? trimmed : null;
}

function boundedNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value)
    ? Math.max(0, Math.round(value * 10) / 10)
    : null;
}

function objectData(value: unknown): BreadcrumbData {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as BreadcrumbData
    : {};
}

function safeNavigationRoute(value: unknown): string | null {
  if (typeof value !== "string" || value.includes("?") || value.includes("#")) return null;
  const route = normalizeDiagnosticPath(value);
  return route.length <= 240 ? route : null;
}

function sanitizeBreadcrumbData(category: string | undefined, value: unknown): BreadcrumbData | undefined {
  const data = objectData(value);
  if (category === "mobile-api.performance") {
    const method = typeof data.method === "string" && HTTP_METHOD_PATTERN.test(data.method) ? data.method : null;
    const path = typeof data.path === "string" && data.path.startsWith("/api/v1/")
      ? normalizeDiagnosticPath(data.path)
      : null;
    const requestId = sanitizeRequestId(data.request_id);
    return {
      cache: ["deduplicated", "fresh", "network", "revalidated"].includes(String(data.cache)) ? data.cache : "network",
      duration_ms: boundedNumber(data.duration_ms),
      error_code: typeof data.error_code === "string" && /^[a-z0-9_]{1,80}$/.test(data.error_code) ? data.error_code : null,
      method,
      outcome: ["api_error", "invalid_response", "network_error", "success"].includes(String(data.outcome)) ? data.outcome : "success",
      path,
      request_id: requestId,
      response_bytes: boundedNumber(data.response_bytes),
      status: boundedNumber(data.status),
    };
  }
  if (category === "mobile.navigation") {
    return {
      from: safeNavigationRoute(data.from),
      reason: typeof data.reason === "string" && NAVIGATION_REASON_PATTERN.test(data.reason) ? data.reason : null,
      to: safeNavigationRoute(data.to),
    };
  }
  return undefined;
}

function sanitizeBreadcrumb(breadcrumb: NonNullable<SanitizableEvent["breadcrumbs"]>[number]) {
  const category = breadcrumb.category;
  const data = sanitizeBreadcrumbData(category, breadcrumb.data);
  const safe = {
    category,
    level: breadcrumb.level,
    timestamp: breadcrumb.timestamp,
    type: breadcrumb.type,
  } as NonNullable<SanitizableEvent["breadcrumbs"]>[number];
  if (data) {
    safe.data = data;
    safe.message = category === "mobile.navigation" ? "route_change" : "request_complete";
  }
  return safe;
}

function sanitizeSpanDescription(value: unknown): string | undefined {
  if (typeof value !== "string" || !value.trim()) return undefined;
  const trimmed = value.trim().slice(0, 300);
  const http = trimmed.match(/^(DELETE|GET|HEAD|OPTIONS|PATCH|POST|PUT)\s+(.+)$/);
  if (http) return `${http[1]} ${normalizeDiagnosticPath(http[2])}`;
  if (trimmed.startsWith("/")) return normalizeDiagnosticPath(trimmed);
  return /^[A-Za-z0-9_+()./:[\]\- ]{1,160}$/.test(trimmed) ? trimmed : "[Filtered]";
}

export function sanitizeSentryEvent<T extends SanitizableEvent>(event: T): T {
  event.user = undefined;
  event.extra = undefined;
  if (event.request) {
    event.request.cookies = undefined;
    event.request.data = undefined;
    event.request.env = undefined;
    event.request.headers = undefined;
    event.request.query_string = undefined;
    event.request.url = typeof event.request.url === "string"
      ? normalizeDiagnosticPath(event.request.url)
      : undefined;
  }
  event.breadcrumbs = event.breadcrumbs?.map(sanitizeBreadcrumb);
  event.transaction = sanitizeSpanDescription(event.transaction);
  return event;
}

export function sanitizeSentryTransaction<T extends SanitizableTransaction>(transaction: T): T {
  sanitizeSentryEvent(transaction);
  transaction.transaction ??= "[Filtered]";
  transaction.spans = transaction.spans?.map((span) => ({
    ...span,
    data: undefined,
    description: sanitizeSpanDescription(span.description),
  }));
  return transaction;
}
