# Calendarization notifications runbook

Status: current
Date: 2026-07-19

## Production configuration

Set `MYSCOOPE_WEB_PUSH_ENABLED=true`, `MYSCOOPE_VAPID_PUBLIC_KEY`,
`MYSCOOPE_VAPID_PRIVATE_KEY` and `MYSCOOPE_VAPID_SUBJECT`. Django `check` fails when
Push is enabled without the complete VAPID set. Rotate keys as a coordinated event:
old browser subscriptions become invalid and users must authorize again.

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
3. Test an installed iOS/iPadOS Home Screen app.
4. Activate accounts in at least two IANA zones and verify the same local configured
   hour maps to different UTC instants.
5. Run the dispatcher twice and verify one delivery per device.
6. Pause/cancel and verify no later event is sent.
7. Enable meal reminders and verify only meals with a valid hour produce an event.

## Incidents and rollback

- Stop outbound delivery immediately with `MYSCOOPE_WEB_PUSH_ENABLED=false`; do not
  delete agendas or events.
- If the scheduler was delayed, restart it normally. Events inside their grace window
  are recovered; older events become `skipped` rather than generating late alerts.
- Inspect Django Admin by event status/failure code. Raw endpoints and encryption keys
  are excluded from list/search displays.
- Roll back UI/worker code while keeping migration 0044; its data is additive and the
  kill switch makes the new delivery path inert.
