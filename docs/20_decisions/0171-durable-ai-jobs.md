# 0171 · Durable asynchronous AI turns

Status: accepted
Date: 2026-08-03

## Decision

Slow AI turns execute outside Gunicorn request threads. The web endpoint stores
an `AIAsyncJob` and returns `202 Accepted`; clients poll a user-scoped result URL.

PostgreSQL is the job authority. It stores idempotency keys, request/result
payloads, attempts, availability, leases and terminal state. Redis is a wake-up
optimization only. A lost Redis signal cannot lose accepted work because workers
always claim from PostgreSQL and reclaim expired leases.

Jobs sharing a conversation lane are serialized. Retries use bounded exponential
backoff, results are private to the submitting user, internal exception details
are not returned to clients, and terminal payloads are retained for 30 days.

Calendar notifications keep their existing specialized durable queue:
`ScheduledNotificationEvent` owns logical work and `NotificationDelivery` owns
idempotent per-device attempts. The continuous Render worker replaces dependence
on an external five-minute cron.

## Rollback

`AI_ASSISTANT_ASYNC_ENABLED=false` restores the synchronous path for new turns.
The AI worker must drain accepted jobs before it is stopped. Schema and completed
job records remain intact during rollback.
