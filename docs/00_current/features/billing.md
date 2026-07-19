# Billing

Status: current BILL00-BILL09 repository implementation
Last updated: 2026-07-19

`billing` is the provider-integration boundary between external collection/tax systems
and the commercial state owned by `accounts`.

## Current contract

- `BillingProduct` maps a provider product to `accounts.AccountPlan`.
- `ProviderSubscription` records provider state without granting access by itself.
- `BillingPayment` records one external payment with a provider-scoped unique ID.
- `BillingEvent` receives only authenticated events and deduplicates provider event IDs.
- `project_provider_subscription` is the explicit projection into
  `accounts.AccountSubscription`.
- `TaxDocument` is a one-to-one outbox/audit record for an approved payment.
- `schedule_tax_document` does no network I/O and is idempotent per payment.
- `billing.application` owns provider-neutral contracts and write use cases.
- `billing.infrastructure` owns Mercado Pago transport/signature verification and fake gateways.
- `billing.interface` owns the provider-authenticated HTTP endpoint.
- `/billing/` exposes the authenticated account-facing overview and opt-in checkout.
- OpenFactura issuance runs out of band with `issue_tax_documents`; provider state is refreshed with `reconcile_billing`.
- Refunds and chargebacks project the subscription to past due and flag the original document for tax review without deleting evidence or guessing a credit note.
- Admin Operations exposes a Billing queue for failed events, past-due subscriptions, failed/rejected DTEs and tax adjustments.

The Mercado Pago webhook route is `/billing/webhooks/mercado-pago/`. It is hidden while
`BILLING_MERCADOPAGO_WEBHOOK_ENABLED=false`. When enabled, it requires an HMAC-SHA256
signature, matching query/body resource IDs, a recent timestamp and a server-to-server
resource read before reconciliation. It only synchronizes provider subscriptions that
were already registered by My Scoope.

Checkout, webhook reception and OpenFactura issuance are implemented but opt-in. All
provider credentials are optional secret environment variables; safe defaults keep real
traffic disabled until sandbox and accounting gates pass.

```text
BILLING_MERCADOPAGO_WEBHOOK_ENABLED=false
BILLING_MERCADOPAGO_CHECKOUT_ENABLED=false
BILLING_PUBLIC_BASE_URL=
BILLING_MERCADOPAGO_ACCESS_TOKEN=
BILLING_MERCADOPAGO_WEBHOOK_SECRET=
BILLING_OPENFACTURA_ENABLED=false
BILLING_OPENFACTURA_API_KEY=
BILLING_OPENFACTURA_ISSUER_JSON={}
```

## Ownership

```text
accounts -> entitlement truth, plan, credits
billing  -> purchase evidence, reconciliation, provider/tax lifecycle
```

Provider callbacks must never update `accounts` directly. They first enter the verified
event/reconciliation flow. OpenFactura emission must start from a persisted approved
payment and reuse the stored `TaxDocument.idempotency_key`.

Operational activation and rollback are defined in
`docs/40_technical/operations/billing_providers_runbook.md`.
