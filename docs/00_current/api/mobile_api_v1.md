# Consumer Mobile API v1

Status: current
Base path: `/api/v1/`
Interface owner: `mobile_api`

## Contract

The consumer API is a versioned, screen-oriented interface over existing Django
application services. It does not reproduce nutrition, calendarization,
commercial or deletion rules inside transport code.

All product responses use:

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

Errors use the same envelope with `ok=false`, empty `data`, and a stable error
object containing `code`, `message` and `details`.

The generated source of truth is `mobile-v1.openapi.json`. CI regenerates the
schema in memory and fails when the committed contract drifts.

## Authentication

- Public clients use authorization code + mandatory PKCE S256.
- Mobile OAuth clients require an app-generated device identifier and a declared
  platform at token exchange.
- Access tokens expire after 15 minutes.
- Refresh tokens expire after 30 days and rotate on every use.
- Reuse of an already-rotated refresh token revokes the whole device session.
- A user can revoke one device without invalidating unrelated devices.
- Existing MCP/ChatGPT authorization-code clients keep their access-only flow.

Mobile scopes are `mobile:read`, `mobile:write` and `mobile:account`.

## Consumer vertical through CML06

The API exposes health, session, device revocation, profile, consumer onboarding,
account entitlements, active calendarized program, Today, weight history/write,
paginated food search, durable AI submit/poll and account deletion.

CML04 adds meal check-ins, derived adherence, program-context measurements,
periodic reviews, reminder settings/upcoming logical events and explicit decisions
for prepared future revisions. Check-ins are append-only; corrections preserve
history. Review summaries are frozen at creation. Revision approval revalidates
that all affected days are strictly future and unexecuted, and the client cannot
submit arbitrary before/after plan snapshots.

CML05 adds `POST /foods/label-captures` as a confirmation endpoint, not an OCR
endpoint. It accepts normalized values only after client review, enforces the
existing food-creation entitlement and creates a private, unverified,
solver-disabled food with an idempotent receipt. Photos and raw OCR text are not
part of the API contract.

CML06 adds `GET /subscriptions` and
`POST /subscriptions/apple/transactions`. The first returns the current effective
plan, independent provider evidence, a stable Apple account token and only active
server-configured Apple product identifiers. It intentionally omits price:
localized price and currency are StoreKit authority. The second accepts StoreKit
2's signed transaction JWS, requires `mobile:write`, verifies it server-side and
updates billing evidence before the native client may finish the transaction.
Nutritionist accounts receive no consumer purchase offer.

Native notification delivery remains CML07; the API already exposes the common
calendarization schedule that each channel must follow. Food libraries,
meal/daily-plan editing and remaining library mutations can be added after the
React Native execution journey proves they are needed; they must preserve the
same envelope, scopes and service boundaries.
