import type { CalendarizationStatus, ReminderSettings } from "@/api/types";

export const LOCAL_REMINDER_OWNER = "myscoope-calendarization";
export const LOCAL_REMINDER_LIMIT = 60;
export const LOCAL_REMINDER_MIN_LEAD_MS = 5_000;

export type LocalReminderEvent = ReminderSettings["upcoming"][number] & {
  scheduledAt: Date;
};

export function localReminderEvents(
  reminders: ReminderSettings,
  now: number = Date.now(),
): LocalReminderEvent[] {
  return reminders.upcoming
    .flatMap((event) => {
      const scheduledAt = new Date(event.scheduled_for_utc);
      return Number.isFinite(scheduledAt.getTime()) && scheduledAt.getTime() > now + LOCAL_REMINDER_MIN_LEAD_MS
        ? [{ ...event, scheduledAt }]
        : [];
    })
    .sort((left, right) => left.scheduledAt.getTime() - right.scheduledAt.getTime())
    .slice(0, LOCAL_REMINDER_LIMIT);
}

export function localReminderIdentifier(eventKey: string): string {
  return `${LOCAL_REMINDER_OWNER}:${eventKey}`;
}

export function shouldScheduleNativeReminders(status: CalendarizationStatus | null): boolean {
  return status === "active" || status === "scheduled";
}
