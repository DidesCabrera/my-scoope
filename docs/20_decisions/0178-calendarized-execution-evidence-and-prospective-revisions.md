# 0178 - Calendarized execution evidence and prospective revisions

Status: accepted
Date: 2026-08-05

## Decision

`ProgramCalendarization` remains the aggregate root of the lived program. Meal
check-ins are append-only `CalendarizedMealExecution` events attached to one
`CalendarizedDay` and one stable meal key from that day's immutable plan
snapshot. Corrections append a reset event; they never edit or delete prior
evidence.

Weight remains user-owned in `WeightLog`. A
`CalendarizationMeasurementContext` links a weight entry to the active
calendarization and optional day without moving or duplicating the measurement.
Periodic `CalendarizationReview` records store subjective scores together with a
server-built adherence and weight summary snapshot.

An adjustment is a `CalendarizationRevision`: a reviewable before/after snapshot
for explicitly selected dates. It can affect only dates after the user's current
local day, rejects days with execution evidence, requires an explicit approval or
rejection and records the decision. Applying an approved revision replaces only
eligible future snapshots and reschedules their pending logical reminder events.

## Consequences

- Planned snapshots and observed execution remain separate facts.
- Today and progress views derive current meal state from append-only evidence.
- Measurement trends can be evaluated in the context of the lived program while
  `WeightLog` remains the personal measurement authority.
- API clients may approve or reject an already prepared revision but cannot post
  arbitrary nutritional snapshots as an adjustment.
- Local notifications, APNs and Web Push remain delivery channels over the same
  calendarization schedule. Native delivery permissions and credentials remain
  CML07 work.
