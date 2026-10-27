import type { CalendarCommitment, CalendarOverviewData } from "@/api/calendar-types";

export type EmptyDaySituation =
  | { kind: "planned"; scheduledPlanDate: string | null; plansCount: number }
  | { kind: "commitment"; commitment: CalendarCommitment }
  | { kind: "empty" }
  | { kind: "unknown" };

export function emptyDaySituation(overview: CalendarOverviewData | null, localDate: string): EmptyDaySituation {
  if (!overview) return { kind: "unknown" };
  if ((overview.future_plans_count ?? 0) > 0) {
    const nextVisiblePlan = overview.days
      .filter((day) => day.has_plan && day.calendar_date > localDate)
      .sort((left, right) => left.calendar_date.localeCompare(right.calendar_date))[0];
    const scheduledPlanDate = nextVisiblePlan?.calendar_date
      ?? (overview.last_scheduled_date && overview.last_scheduled_date > localDate
        ? overview.last_scheduled_date
        : null);
    return { kind: "planned", scheduledPlanDate, plansCount: overview.future_plans_count ?? 0 };
  }
  const commitment = overview.days
    .filter((day) => day.calendar_date >= localDate)
    .sort((left, right) => left.calendar_date.localeCompare(right.calendar_date))
    .flatMap((day) => day.commitments ?? [])[0];
  return commitment ? { kind: "commitment", commitment } : { kind: "empty" };
}
