import type { CalendarCommitment, CalendarCommitmentKind, CalendarDay } from "@/api/calendar-types";

export type CommitmentListRange = "upcoming" | "all";
export type CommitmentScope = "all" | CalendarCommitmentKind;

export function commitmentsForMonth(days: CalendarDay[], visibleMonth: string, today: string, scope: CommitmentScope, range: CommitmentListRange): CalendarCommitment[] {
  return days
    .filter((day) => day.calendar_date.startsWith(`${visibleMonth}-`) && (range === "all" || day.calendar_date >= today))
    .flatMap((day) => (day.commitments ?? []).filter((item) => scope === "all" || item.kind === scope));
}
