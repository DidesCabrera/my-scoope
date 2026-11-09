import type { CalendarCommitment, CalendarCommitmentKind, CalendarDay } from "@/api/calendar-types";

export type CommitmentScope = "all" | CalendarCommitmentKind;

function shiftDate(value: string, days: number): string {
  const date = new Date(`${value}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function commitmentsForUpcomingDays(days: CalendarDay[], today: string, dayCount: number, scope: CommitmentScope): CalendarCommitment[] {
  const endDate = shiftDate(today, dayCount);
  return days
    .filter((day) => day.calendar_date >= today && day.calendar_date < endDate)
    .flatMap((day) => (day.commitments ?? []).filter((item) => scope === "all" || item.kind === scope));
}
