# Decision 0153: calendarization uses immutable daily snapshots and idempotent Web Push deliveries

Status: accepted
Date: 2026-07-19

## Context

Weekly programs are editable relative templates. A user needs to activate one on real
dates and receive reminders at a configurable local time without server timezone leaks
or duplicate device notifications.

## Decision

Calendarization is a separate execution layer. Activation materializes one versioned,
self-contained daily JSON snapshot per program slot. One partial database constraint
allows only one scheduled, active or paused calendarization per user. Incomplete
programs are accepted only after explicit confirmation and empty days generate no event.

Scheduling combines the calendar date and configured time inside an IANA timezone,
then persists the UTC instant and grace window. A logical `ScheduledNotificationEvent`
is separate from each `NotificationDelivery`; unique keys protect both layers. Web Push
uses explicit per-device subscriptions, VAPID, SSRF-resistant endpoint validation,
bounded retries, expired-subscription deactivation and a global kill switch.

## Consequences

- Program edits/deletion cannot silently alter an active schedule.
- Push can be disabled while the Calendarizar dashboard remains useful.
- A recurring external scheduler invokes an idempotent management command; Celery is
  unnecessary until production evidence justifies it.
- Real production activation requires credentials and staging smoke on supported
  browsers/devices, including installed iOS/iPadOS Home Screen apps.
