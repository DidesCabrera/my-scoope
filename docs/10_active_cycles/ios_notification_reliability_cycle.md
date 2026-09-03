# iOS Notification Reliability Cycle

Status: repository implementation complete — physical iPhone evidence partially recorded
Date: 2026-09-03
Cycle code: INR

## Objective

Make meal and daily-plan notifications follow the active program reliably on a
physical iPhone, both with direct APNs delivery and with the deterministic local
fallback used while APNs is disabled.

## Invariants

- `ScheduledNotificationEvent` remains the authority for date, local time,
  timezone and UTC delivery instant.
- APNs and local delivery are mutually exclusive on each iPhone.
- Only `scheduled` and `active` calendarizations may retain local requests.
- Pausing, cancelling, replacing, changing a meal hour or applying a future
  revision reconciles the iPhone immediately.
- Local scheduling never includes elapsed events and remains bounded to the next
  60 requests. The window is renewed whenever the app starts or returns active.
- Permission is requested only after the user explicitly enables notifications.

## Patch sequence

| Patch | Status | Exit evidence |
| --- | --- | --- |
| INR00 · Failure characterization | completed | Elapsed pending events, the 20-event starvation window, stale lifecycle requests and cold-start navigation were reproduced in code/data. |
| INR01 · Future server projection | completed | `/api/v1/today` returns only the next 60 future pending events; backend regression covers elapsed exclusion and bounding. |
| INR02 · Native scheduling policy | completed | Invalid/elapsed events are rejected again on-device, requests use deterministic identifiers and concurrent reconciliations are serialized. |
| INR03 · Lifecycle reconciliation | completed | Activation, pause/resume/cancel, meal-hour change and approved revisions reconcile immediately; logout clears owned requests. |
| INR04 · App lifecycle and navigation | completed | Startup/foreground refreshes the rolling window and both initial and live notification responses open Today. |
| INR05 · Automated verification | completed | Django notification/API tests, mobile unit/contract tests, TypeScript, lint, iOS bundle export and a generic signed Release build pass. |
| INR06 · Physical iPhone gate | in progress | TestFlight build 11 delivered notifications successfully on a physical iPhone. Detailed device metadata and the remaining offline, stale-request, cold-start, denial and duplicate-channel checks are still pending. |

## Physical evidence log

### 2026-09-03 — TestFlight build 11

- Environment: staging.
- Distribution: TestFlight, build 11.
- Device: physical iPhone; model, iOS version and timezone were not recorded.
- Result reported by the tester: notifications were received successfully.
- Scope limitation: this confirms basic notification delivery only. It does not
  yet close the offline fallback, changed-time cancellation, pause/cancel,
  cold-start navigation, denied-permission, APNs/local exclusivity or duplicate
  delivery checks below.

## Physical acceptance protocol

Record iPhone model, iOS version, build number and timezone. Do not include account
or nutrition details in screenshots or logs.

1. Install a signed development/TestFlight build connected to staging.
2. Keep `MYSCOOPE_APNS_ENABLED=false`, activate a program with meal reminders and
   accept the iOS permission prompt.
3. Open Recordatorios and confirm a positive local-request count. Put the app in
   background, disconnect the network and verify one near-future meal alert.
4. Change a later meal hour, then verify the old request does not fire and the new
   one does.
5. Pause and cancel in separate runs; verify no owned alert fires afterward.
6. Force-quit the app, tap an alert and verify Today opens after session restore.
7. Deny permission on a clean install and verify the program and check-ins remain
   usable while Recordatorios reports the denied state.
8. Configure APNs in both API and worker, resync a TestFlight build, verify local
   requests are removed and exactly one remote alert arrives.
9. Run the dispatcher twice and verify one `NotificationDelivery` per event/device.

INR is closed only after all INR06 evidence is recorded. The successful build 11
test proves basic delivery on a physical iPhone, but does not by itself prove the
remaining lifecycle cases, Focus-mode behavior or APNs/local exclusivity.
