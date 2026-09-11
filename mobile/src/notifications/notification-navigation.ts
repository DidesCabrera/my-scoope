import type { Href } from "expo-router";

import type { ReminderSettings } from "@/api/types";

type NotificationData = Record<string, unknown>;

function internalRoute(value: unknown): Href | null {
  if (typeof value !== "string") return null;
  if (value === "/today" || /^\/program\/days\/\d+(?:\/meals\/[^/?#]+)?$/.test(value)) {
    return value as Href;
  }
  return null;
}

export function notificationRoute(data: NotificationData | undefined): Href {
  const notificationData = data ?? {};
  const namespaced = notificationData.myscoope;
  const namespacedData = namespaced && typeof namespaced === "object"
    ? namespaced as NotificationData
    : {};
  return internalRoute(notificationData.url)
    ?? internalRoute(notificationData.target)
    ?? internalRoute(namespacedData.url)
    ?? "/today";
}

export function notificationRouteForReminder(
  event: ReminderSettings["upcoming"][number],
): Href {
  const dayRoute = `/program/days/${event.calendarized_day_id}`;
  if (event.event_type !== "meal_reminder" || !event.meal_key) return dayRoute as Href;
  return `${dayRoute}/meals/${encodeURIComponent(event.meal_key)}` as Href;
}
