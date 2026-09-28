# Billing providers runbook

Status: current
Last updated: 2026-09-28

## Safe default

Keep `BILLING_PADDLE_CHECKOUT_ENABLED`, `BILLING_PADDLE_WEBHOOK_ENABLED`,
`BILLING_MERCADOPAGO_CHECKOUT_ENABLED`, `BILLING_MERCADOPAGO_WEBHOOK_ENABLED` and
`BILLING_APPLE_PURCHASES_ENABLED`, `BILLING_APPLE_NOTIFICATIONS_ENABLED` and
`BILLING_OPENFACTURA_ENABLED` false. Keep Google Play subscription and credit-pack
refund reconciliation disabled until their sandbox evidence is complete. This
preserves all history while stopping new traffic.

## Paddle sandbox activation

1. Run `.venv/bin/python manage.py seed_billing_catalog`. This creates only missing
   canonical offers; it reports drift and never overwrites an existing price.
2. In Paddle sandbox, create Basic and Pro products with monthly and annual prices.
   Free remains an internal plan and does not need a Paddle product.
3. Map the returned IDs with `configure_paddle_catalog --environment sandbox`
   and its four `pro_`/`pri_` arguments. Mapping a replacement price deactivates the
   former mapping but does not delete or rewrite it.
4. Configure a sandbox client-side token, API key, notification destination secret,
   sandbox API URL and an HTTPS staging base URL.
5. Register `/billing/webhooks/paddle/` for subscription and transaction lifecycle
   notifications. Verify invalid signatures, stale timestamps, duplicate deliveries,
   unknown prices and mismatched signed checkout references.
6. Enable webhooks first, then checkout. Complete Basic/Pro monthly/annual purchases
   and exercise renewal, past-due, cancellation, hosted customer-portal and refund
   simulations. Confirm portal links are generated server-side and expire as expected.
7. Confirm that access changes only from verified events and that Paddle payments do
   not create OpenFactura tax-document jobs.

Do not use live credentials or IDs in sandbox. The `BILLING_PADDLE_ENVIRONMENT`, client
token and API URL must agree or the environment diagnostic fails closed.

## Mercado Pago activation

1. Create separate test and production credentials and a recurring preapproval plan.
2. Map its ID to an active `BillingProduct` and `accounts.AccountPlan`.
3. Configure token, webhook secret, API base and HTTPS `BILLING_PUBLIC_BASE_URL`.
4. Test invalid signatures, replay, duplicate delivery and unknown resources before enabling the webhook.
5. Complete a sandbox subscription and verify the server snapshot before enabling checkout.

Browser return parameters never grant access. Only verified provider state projects to `AccountSubscription`.

## Apple App Store activation

1. Complete App Store Connect agreements, tax and banking setup. Create the
   auto-renewable subscription group and final product identifiers/prices.
2. Map the four identifiers with `configure_apple_catalog --environment live`
   and its Basic/Pro monthly/annual arguments. The command snapshots the canonical
   offers and is safe to repeat. Do not expose a product until this mapping is
   deliberate.
3. Configure the sandbox bundle ID and, for production, numeric Apple app ID.
   Register `/billing/webhooks/apple-app-store/` as the App Store Server
   Notifications V2 URL.
4. Configure the In-App Purchase API `.p8` content, key ID and issuer ID for
   lifecycle reconciliation. The public Apple Root CA G3 certificate is bundled;
   private keys remain environment secrets.
5. Enable notifications first. Confirm invalid JWS rejection, notification replay
   idempotency and lifecycle projection. Run
   `.venv/bin/python manage.py reconcile_apple_subscriptions --dry-run`.
6. In a development/TestFlight build on a physical iPhone, buy and restore each
   product with a sandbox tester. Confirm localized StoreKit pricing, matching
   `appAccountToken`, server verification before finish and renewal/expiration/
   grace/revocation behavior.
7. Enable purchases only after that evidence passes. A simultaneous active Apple
   and Mercado Pago row must appear in Admin Operations and be resolved manually
   with the user; never delete evidence or cancel a provider automatically.

## OpenFactura activation

1. Have a Chilean tax professional approve DTE type, issuer fields, IVA treatment, service indicator, glosa and credit-note procedure.
2. Configure the sandbox API key and approved `BILLING_OPENFACTURA_ISSUER_JSON`.
3. Enable OpenFactura and run `.venv/bin/python manage.py issue_tax_documents --limit 1`.
4. Confirm token, folio and SII state with `.venv/bin/python manage.py reconcile_billing --limit 10`.
5. Test duplicate execution with the same key. Automated retries stop after 23 hours because the provider documents a 24-hour idempotency window; reconcile older uncertain outcomes manually.

## Daily operations

- Review Admin Operations → Billing and Django Admin filters.
- Schedule `reconcile_billing` and alert on command failures.
- Schedule `reconcile_apple_subscriptions` and alert on command failures when
  Apple is active.
- The daily housekeeping job invokes `scripts/run_billing_reconciliation.sh`.
  Its Google Play subscription and credit-pack refund checks run independently;
  either failure makes the job fail. Both are inert until their separate
  `BILLING_GOOGLE_PLAY_*_RECONCILIATION_ENABLED` flags are enabled.
- Investigate failed events, past-due subscriptions, failed/rejected DTEs and `adjustment_required`.
- A refund or chargeback revokes access and opens tax review; it does not automatically void a boleta or emit a credit note.

## Rollback

Disable the provider flags. Do not delete subscriptions, payments, events, Apple
account tokens or tax documents. Reconcile external state before re-enabling.

## Google Play staging and lifecycle gate

Keep the existing `myscoope_basic` and `myscoope_pro` subscriptions and their
monthly/annual base plans, plus the three `myscoope.credits.*` one-time products;
do not duplicate product IDs. A purchase changes entitlements only after the
Google Play Developer API verifies its token and account binding.

`reconcile_google_play_subscriptions` reads stored purchase tokens and refreshes
renewal, grace, hold, cancellation and expiration evidence. It defaults to a
dry run; `--apply` changes the account projection. The scheduled invocation
also uses `--if-enabled`, so set
`BILLING_GOOGLE_PLAY_SUBSCRIPTION_RECONCILIATION_ENABLED=true` only after a
staging purchase and lifecycle test. The separate
`reconcile_google_play_credit_pack_refunds` command likewise defaults to a dry
run and must remain disabled in production until a test purchase, void and
credit reversal have been observed end to end. It checks both Google's Voided
Purchases feed (refunds with revocation and chargebacks) and each still-approved
credit-pack purchase individually. The latter is necessary because Google omits
developer refunds made without "revoke" from the Voided Purchases feed. A full
refund is applied only when the individual purchase has the matching order,
product, account and environment, a single unit, state `CANCELLED`, and zero
refundable quantity. Missing or conflicting verification fails the job without
silently removing credits. Keep the recurring job enabled and monitor its
runtime as sales volume grows: individual checks use one Google API request per
still-approved Google credit-pack purchase.
