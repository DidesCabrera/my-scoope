# Decision 0156: Email delivery uses layered abuse protection and durable attempts

Status: accepted
Date: 2026-07-27

## Context

My Scoope used Resend through Django SMTP for mandatory account verification and
direct calls from five share views. Signup had only a per-minute IP decorator backed
by the default process-local cache. Repeating an existing share could send another
email without creating a new share row, so product share metrics did not represent
provider consumption.

Email verification proves control only after an email has already been consumed. It
cannot be the sole defense against automated signup.

## Decision

Traditional signup uses layered controls: optional-by-environment Turnstile with
mandatory server validation when enabled, multi-window IP/email limits, allauth's
action-specific limits and a shared Redis cache in production.

Password-reset requests for unknown addresses retain allauth's generic response but
do not send the optional "Unknown Account" email. Provider evidence showed that this
message represented 109 of 245 recent sends and produced most observed bounces.

`email_delivery.EmailDeliveryAttempt` is the durable operational record for protected
outbound email. Authentication adapters audit verification and password-reset mail.
Share views delegate to one policy service.

Share email is non-critical. Existing users receive the shared object in Inbox
without an email, one share record can generate at most one initial email, and global,
actor, recipient and cooldown limits apply before SMTP. A dedicated kill switch can
stop share email without disabling account email or the sharing feature itself.

## Consequences

- Turnstile or an IP limit alone is not treated as sufficient.
- Production rate-limit correctness depends on external Redis configuration.
- Repeating a share form no longer functions as an implicit resend operation.
- Critical account email is not consumed by the share-email daily budget.
- Provider-level delivery, bounce and complaint state still lives in Resend until a
  later signed-webhook cycle is justified by observed volume.
- Cloudflare, Render Key Value and production environment configuration remain
  deployment gates outside repository code.
