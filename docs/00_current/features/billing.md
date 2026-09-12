# Billing

Status: current BILL00-BILL09 + CML06 repository implementation
Last updated: 2026-09-11

`billing` is the provider-integration boundary between external collection/tax systems
and the commercial state owned by `accounts`.

## Current contract

- `BillingOffer` is the runtime authority for amount, currency and billing cadence.
- `BillingProduct` is an immutable provider/environment catalog snapshot mapped
  to a `BillingOffer`; old mappings remain available for subscription history.
- `ProviderSubscription` records provider state without granting access by itself.
- `BillingPayment` records one external payment with a provider-scoped unique ID.
- `BillingEvent` receives only authenticated events and deduplicates provider event IDs.
- `project_provider_subscription` deterministically aggregates every verified
  provider row into the one `accounts.AccountSubscription` authority.
- `AppleAppAccountToken` supplies a stable opaque UUID for StoreKit ownership
  binding without exposing a database user ID.
- `TaxDocument` is a one-to-one outbox/audit record for an approved payment.
- `schedule_tax_document` does no network I/O and is idempotent per payment.
- `billing.application` owns provider-neutral contracts and write use cases.
- `billing.infrastructure` owns Paddle and Mercado Pago signature verification,
  Apple signed-data/App Store Server API verification and fake gateways.
- `billing.interface` owns the provider-authenticated HTTP endpoint.
- `/billing/` exposes the authenticated account-facing overview and opt-in checkout.
- OpenFactura issuance runs out of band with `issue_tax_documents`; provider state is refreshed with `reconcile_billing`.
- Refunds and chargebacks project the subscription to past due and flag the original document for tax review without deleting evidence or guessing a credit note.
- Admin Operations exposes a Billing queue for failed events, past-due subscriptions, failed/rejected DTEs and tax adjustments.
- Admin Operations also exposes accounts with simultaneous active providers;
  evidence is never silently removed to hide a possible double charge.

The Mercado Pago webhook route is `/billing/webhooks/mercado-pago/`. It is hidden while
`BILLING_MERCADOPAGO_WEBHOOK_ENABLED=false`. When enabled, it requires an HMAC-SHA256
signature, matching query/body resource IDs, a recent timestamp and a server-to-server
resource read before reconciliation. It only synchronizes provider subscriptions that
were already registered by My Scoope.

Paddle sandbox checkout and webhook reception are implemented but opt-in. Paddle.js
receives only a client-side token and a signed My Scoope checkout reference. Subscription
access is projected only after an authenticated Paddle webhook maps the `pri_` price back
to an active provider snapshot. Paddle payments never schedule an OpenFactura document,
because Paddle is the Merchant of Record. An authenticated Paddle subscriber can open a
short-lived hosted customer-portal session to manage payment details or cancellation;
the API key remains server-side.

Checkout, webhook reception and OpenFactura issuance are opt-in. All
provider credentials are optional secret environment variables; safe defaults keep real
traffic disabled until sandbox and accounting gates pass.

The Apple notification route is `/billing/webhooks/apple-app-store/` and is
hidden until `BILLING_APPLE_NOTIFICATIONS_ENABLED=true`. It accepts only App
Store Server Notifications V2 whose signed payload and nested transaction pass
Apple's official verifier. Mobile purchase JWS values enter through
`POST /api/v1/subscriptions/apple/transactions`; product, account token, bundle
and environment are verified before projection and transaction finalization.
The inbox stores normalized evidence, never the raw JWS.

```text
BILLING_PADDLE_ENVIRONMENT=sandbox
BILLING_PADDLE_CHECKOUT_ENABLED=false
BILLING_PADDLE_WEBHOOK_ENABLED=false
BILLING_PADDLE_CLIENT_TOKEN=
BILLING_PADDLE_API_KEY=
BILLING_PADDLE_WEBHOOK_SECRET=
BILLING_PADDLE_API_BASE_URL=https://sandbox-api.paddle.com
BILLING_PADDLE_TIMEOUT_SECONDS=10
BILLING_PADDLE_WEBHOOK_TOLERANCE_SECONDS=5
BILLING_MERCADOPAGO_WEBHOOK_ENABLED=false
BILLING_MERCADOPAGO_CHECKOUT_ENABLED=false
BILLING_PUBLIC_BASE_URL=
BILLING_MERCADOPAGO_ACCESS_TOKEN=
BILLING_MERCADOPAGO_WEBHOOK_SECRET=
BILLING_APPLE_NOTIFICATIONS_ENABLED=false
BILLING_APPLE_PURCHASES_ENABLED=false
BILLING_APPLE_ENVIRONMENT=sandbox
BILLING_APPLE_BUNDLE_ID=com.myscoope.app
BILLING_APPLE_APP_ID=
BILLING_APPLE_IN_APP_PURCHASE_KEY=
BILLING_APPLE_KEY_ID=
BILLING_APPLE_ISSUER_ID=
BILLING_APPLE_ONLINE_CHECKS=true
BILLING_OPENFACTURA_ENABLED=false
BILLING_OPENFACTURA_API_KEY=
BILLING_OPENFACTURA_ISSUER_JSON={}
```

## Ownership

```text
accounts -> entitlement truth, plan, credits
billing  -> offer-price truth, provider mappings, purchase evidence and lifecycle
```

Provider callbacks must never update `accounts` directly. They first enter the verified
event/reconciliation flow. OpenFactura emission must start from a persisted approved
payment and reuse the stored `TaxDocument.idempotency_key`.

Operational activation and rollback are defined in
`docs/40_technical/operations/billing_providers_runbook.md`.
