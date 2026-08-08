export type SanitizableEvent = {
  user?: unknown;
  extra?: unknown;
  request?: {
    cookies?: unknown;
    data?: unknown;
    env?: unknown;
    headers?: unknown;
    query_string?: unknown;
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

export function sanitizeSentryEvent<T extends SanitizableEvent>(event: T): T {
  event.user = undefined;
  event.extra = undefined;
  if (event.request) {
    event.request.cookies = undefined;
    event.request.data = undefined;
    event.request.env = undefined;
    event.request.headers = undefined;
    event.request.query_string = undefined;
  }
  event.breadcrumbs = event.breadcrumbs?.map((breadcrumb) => ({
    category: breadcrumb.category,
    level: breadcrumb.level,
    timestamp: breadcrumb.timestamp,
    type: breadcrumb.type,
  }));
  return event;
}
