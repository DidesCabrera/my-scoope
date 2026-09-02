# Calendarization notifications runbook

Status: current
Date: 2026-09-02

## Production configuration

Set `MYSCOOPE_WEB_PUSH_ENABLED=true`, `MYSCOOPE_VAPID_PUBLIC_KEY`,
`MYSCOOPE_VAPID_PRIVATE_KEY` and `MYSCOOPE_VAPID_SUBJECT`. Django `check` fails when
Push is enabled without the complete VAPID set. Rotate keys as a coordinated event:
old browser subscriptions become invalid and users must authorize again.

For direct iOS delivery, configure `MYSCOOPE_APNS_ENABLED=true` only after all of
`MYSCOOPE_APNS_KEY_ID`, `MYSCOOPE_APNS_TEAM_ID`,
`MYSCOOPE_APNS_PRIVATE_KEY` and `MYSCOOPE_APNS_BUNDLE_ID=com.myscoope.app` are
available to both the web process and notification worker. Store the `.p8`
contents as a secret; escaped `\n` line breaks are accepted. Django checks fail if
APNs is enabled incompletely.

The iPhone registration endpoint returns `apns` only when that configuration is
complete. In that mode the app removes its My Scoope local requests. Otherwise it
uses local notifications generated from the same UTC events. Do not alter this
exclusive policy: local + APNs together would duplicate reminders.

Use a Render Background Worker (or an equivalent scheduler with five-minute cadence):

```text
python manage.py run_calendar_notification_worker --interval 300 --limit 100
```

For platforms that can invoke jobs every five minutes, call the one-shot command
`python manage.py dispatch_calendar_notifications --limit 100` instead. Do not use a
cadence larger than the declared 0–5 minute delivery SLA.

Run housekeeping daily:

```text
python manage.py prune_calendarization_data --event-days 90 --subscription-days 30
```

## Staging gate

1. Apply migrations and run `python manage.py check`.
2. Test Chrome/Firefox/Safari-compatible PWA subscription where supported.
3. On a signed physical iPhone build, enable a daily or meal reminder from an explicit
   user action, grant notification permission and verify the device subscription is
   attached to its active OAuth device session.
4. With APNs disabled, open Recordatorios and verify a positive local-request count.
   Background the app, disconnect the network and verify delivery of a near-future
   meal event.
5. Enable APNs with a sandbox key, resync and verify local requests are removed and
   one APNs alert arrives. Repeat with the production/TestFlight environment.
6. Activate accounts in at least two IANA zones and verify the same local configured
   hour maps to different UTC instants.
7. Run the dispatcher twice and verify one delivery per device.
8. Change a future meal hour and verify the old local request is removed and the new
   instant is delivered. Pause, cancel and replace in separate runs and verify no stale
   request is sent.
9. Enable meal reminders and verify only meals with a valid hour produce an event.
10. Force-quit the app, tap an alert and verify Today opens after session restoration.
11. Deny permission and verify Today/check-ins remain usable without scheduled alerts.
12. Record device, iOS, build and timestamps without account or nutrition PII.

## Incidents and rollback

- Stop outbound delivery immediately with `MYSCOOPE_WEB_PUSH_ENABLED=false`; do not
  delete agendas or events.
- Stop native remote delivery with `MYSCOOPE_APNS_ENABLED=false`; the next app sync
  reverts that device to local reminders without deleting the logical agenda.
- If the scheduler was delayed, restart it normally. Events inside their grace window
  are recovered; older events become `skipped` rather than generating late alerts.
- Inspect Django Admin by channel/status/failure code. Raw web endpoints, APNs
  device tokens and encryption/provider keys are excluded from list/search displays.
- Roll back UI/worker code while keeping migrations 0044 and 0050; their data is
  additive and the two kill switches make outbound delivery inert.
