# Decision 0154: Billing separates payment collection, entitlements and tax documents

Status: accepted
Date: 2026-07-19

## Context

`accounts` already owns commercial plans, subscriptions, credits and entitlements.
My Scoope will initially collect recurring payments through Mercado Pago in Chile and
issue electronic receipts through OpenFactura. Treating both providers as one
synchronous checkout operation would couple access, money collection and SII document
availability, and would make retries capable of duplicating tax documents.

## Decision

Create a separate Tier 1 Django app named `billing`. Its payment and tax workflows are
called from multiple entry points (webhooks, checkout, workers, reconciliation and
operations), so the project rule requires explicit `application`, `infrastructure` and
`interface` boundaries from the beginning. Django ORM models remain in `billing.models`.

`billing` owns provider product mappings, observed provider subscriptions, individual
payments, an idempotent authenticated-event inbox and the tax-document outbox. Verified
provider state is projected into `accounts.AccountSubscription`; provider rows never
become the direct entitlement source.

Mercado Pago is the first payment adapter. A signed webhook only schedules or triggers
server-to-server verification of the referenced resource. OpenFactura is a separate
downstream adapter. One approved payment can create at most one persisted tax-document
request, whose `Idempotency-Key` remains stable across retries.

## Consequences

- Payment-provider outages do not erase existing account state.
- OpenFactura/SII delays do not cause a second charge or duplicate receipt.
- Duplicate webhook deliveries are safe.
- Apple App Store, Google Play or another web collector can be added as adapters while
  preserving the same `accounts` boundary.
- Checkout and tax emission are opt-in and remain disabled until sandbox, security,
  accounting and operational gates pass.
- Refunds/chargebacks revoke access and create a tax-review signal. Automatic credit
  notes are intentionally deferred until the Chilean DTE contract is approved.
