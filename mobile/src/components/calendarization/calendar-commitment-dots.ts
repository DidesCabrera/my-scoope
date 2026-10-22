import type { CalendarCommitment, CalendarCommitmentKind } from "@/api/calendar-types";

export function commitmentDotKinds(commitments: Pick<CalendarCommitment, "kind">[] | undefined, draftKind?: CalendarCommitmentKind): CalendarCommitmentKind[] {
  return [...new Set([...(commitments ?? []).map((item) => item.kind), ...(draftKind ? [draftKind] : [])])];
}
