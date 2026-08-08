# 0178 Calendarization as the lived program

Status: accepted
Date: 2026-08-05

## Context

Calendarization already materializes immutable daily snapshots on real dates and
owns durable daily/meal reminder events. A separate mobile execution timeline
would duplicate the original purpose of this boundary and create ambiguity about
which program the user is actually following.

## Decision

`Program` remains the editable template. `ProgramCalendarization` is the lived
program and aggregate root for:

- dated DailyPlan snapshots;
- planned meals and meal times;
- reminder coordination;
- future meal/day execution evidence;
- measurement context and progress reviews;
- reviewable revisions of future unexecuted days.

Execution records may be separate models, but they must belong to a calendarized
day and never form a second schedule. Weight remains user-owned and may reference
the active calendarization as context.

Adjustments preserve past days and any current day whose execution began. An
approved adjustment creates auditable revision evidence, reprojects only eligible
future days and reschedules their pending reminders.

## Consequences

- Today resolves from the one current calendarization.
- Adherence does not mutate planned snapshots.
- Program template edits cannot rewrite an active lived program.
- Local iOS notifications, APNs and Web Push are delivery mechanisms over the
  calendarization schedule, not competing authorities.
