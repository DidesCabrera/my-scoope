# Production deployment runbook

Status: current
Date: 2026-08-03

## Versioned topology

`render.yaml` is the deployment authority for:

```text
my-scoope                       Django/Gunicorn web service
my-scoope-ai-jobs               durable AI turn worker
my-scoope-notifications         continuous five-minute notification dispatcher
my-scoope-calendar-housekeeping daily retention job
my-scoope-postgres              PostgreSQL 17
my-scoope-cache                 private Render Key Value
```

The continuous worker owns the five-minute notification cadence. Do not also
configure a five-minute one-shot notification cron, because two schedulers would
compete for the same delivery work. The cron in the Blueprint only performs
daily retention housekeeping.

AI jobs are persisted in PostgreSQL before the web request returns `202`.
Redis only signals that work is available, so restarting or evicting Redis does
not lose a turn. The AI worker recovers expired leases and retries failures with
bounded backoff. `ScheduledNotificationEvent` and `NotificationDelivery` provide
the equivalent durable/idempotent database queue for calendar notifications.

Render Blueprint reference:
https://render.com/docs/blueprint-spec

## First adoption

1. Compare Blueprint names with existing dashboard resources. Rename the YAML
   entries before applying if the existing resource names differ; do not create a
   second production database or web service accidentally.
2. Validate `render.yaml` with the Render CLI or Blueprint validation API.
3. Create/apply a Blueprint instance from the repository.
4. Populate all `sync: false` values. At minimum, configure Sentry, OpenAI, email
   and provider credentials for every feature that will be enabled.
5. Keep `MYSCOOPE_WEB_PUSH_ENABLED=false` until both VAPID keys and a real browser
   smoke test are ready; then set it to `true` on the notification worker.
6. Verify the pre-deploy command runs migrations and `check --deploy` before the
   new release receives traffic.

## Per-deploy checks

```text
build
  -> install pinned dependencies
  -> collect static assets
  -> run Django checks

pre-deploy
  -> apply migrations
  -> run Django deployment checks

start
  -> Gunicorn binds to Render's PORT
  -> Render probes /healthz/
```

The build phase must never mutate the database. Schema changes only run in the
paid service's pre-deploy phase so a failed migration prevents the release.

## Smoke checklist

- `/healthz/` returns `200 {"status": "ok"}`.
- Login by password and Google OAuth work.
- A read and write backed by PostgreSQL survive a web redeploy.
- Redis-backed rate limiting works across more than one web process.
- One AI turn records `AIUsageEvent` and commercial account-credit correlation.
- One AI submit returns `202`, reaches `succeeded` through
  `run_ai_job_worker`, and its poll URL is private to the submitting user.
- The notification worker dispatches a due event once, then remains idempotent.
- Sentry receives an intentional non-sensitive test error and performance trace.

## Rollback

Use Render's previous deploy rollback for application failures. Do not roll back
through a destructive reverse migration unless that migration has a reviewed
reverse path. For a database incident, follow
`docs/40_technical/operations/postgres_backup_restore_runbook.md`.

To roll back only asynchronous web behavior, set
`AI_ASSISTANT_ASYNC_ENABLED=false` on the web service. Keep the worker running
until already queued jobs are terminal; disabling the worker first can strand
accepted jobs in `queued` state.
