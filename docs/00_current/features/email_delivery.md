# Email delivery and abuse protection

Status: current
Last updated: 2026-07-27

## Responsibility

`email_delivery` owns the durable audit trail and delivery policy for outbound
transactional email. Authentication remains owned by `accounts`/allauth and share
records remain owned by `notas`; neither area calls the SMTP transport directly for
the protected flows.

## Current contract

- Traditional signup can be protected by Cloudflare Turnstile. When enabled, the
  server validates the token, action and configured hostname allowlist before allauth creates
  the account or sends verification mail.
- Google OAuth remains trusted through its verified-email contract and does not use
  the traditional signup challenge.
- Signup has burst, daily-IP and daily-email limits. Allauth retains separate limits
  for confirmation and password reset.
- Production must configure `CACHE_URL` to make cache-backed limits shared across
  processes and restarts. Local development intentionally uses local-memory cache.
- Account verification and password-reset deliveries are recorded as
  `EmailDeliveryAttempt` rows.
- Password-reset requests for unknown addresses keep a generic response but send no
  email, preventing account enumeration without consuming provider quota.
- Share invitations require a verified sender, are globally and per-user/per-recipient
  budgeted, and have a per-recipient cooldown.
- A share delivered directly into an existing user's Inbox does not send email.
- The initial email for a share is idempotent by share record. Repeating the form
  does not send a second email.
- Provider exceptions are stored only by exception class; credentials and SMTP
  response bodies are not persisted.

## Operational controls

`EMAIL_SHARE_DELIVERY_ENABLED` is the kill switch for non-critical share email. It
does not disable account verification, password reset, share creation or Inbox
delivery.

The Django admin exposes delivery attempts for investigation. Resend remains the
provider-side source for delivery, bounce and complaint evidence until signed
webhooks are implemented.

## External rollout gates

- Cloudflare widget and secret keys must be created for the production hostname.
- Render Key Value must be provisioned and its internal Redis URL assigned to
  `CACHE_URL`.
- Production must set `TURNSTILE_ENABLED=true` only after both keys and hostname are
  configured.
- A staging signup, duplicate-share and existing-recipient Inbox smoke must pass
  before production rollout.
