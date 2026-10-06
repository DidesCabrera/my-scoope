# Billing providers runbook

Status: current
Last updated: 2026-09-28

## Safe default

Keep `BILLING_PADDLE_CHECKOUT_ENABLED`, `BILLING_PADDLE_WEBHOOK_ENABLED`,
`BILLING_MERCADOPAGO_CHECKOUT_ENABLED`, `BILLING_MERCADOPAGO_WEBHOOK_ENABLED` and
`BILLING_APPLE_PURCHASES_ENABLED`, `BILLING_APPLE_NOTIFICATIONS_ENABLED`,
`BILLING_APPLE_SANDBOX_PURCHASES_ENABLED`,
`BILLING_APPLE_SANDBOX_NOTIFICATIONS_ENABLED` and
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
2. Map the four identifiers twice: with `configure_apple_catalog --environment live`
   and `configure_apple_catalog --environment sandbox`. Apple uses the same Product
   IDs in StoreKit, while the signed transaction determines which catalog row is
   authoritative. Map the three credit packs in both environments too. The commands
   snapshot the canonical offers and are safe to repeat.
   The production predeploy script performs these idempotent mappings so a newly
   deployed production database exposes the expected StoreKit identifiers; inspect
   its output for catalog drift before enabling purchases.
3. Configure the bundle ID, numeric Apple app ID and
   `BILLING_APPLE_ENVIRONMENT=production`. Register
   `/billing/webhooks/apple-app-store/production/` as the production App Store Server
   Notifications V2 URL and `/billing/webhooks/apple-app-store/sandbox/` as its
   sandbox URL.
4. Configure the In-App Purchase API `.p8` content, key ID and issuer ID for
   lifecycle reconciliation. The public Apple Root CA G3 certificate is bundled;
   private keys remain environment secrets.
5. In Django Admin, grant active, time-limited `AppleSandboxAccess` only to the
   dedicated internal/App Review account. Never authorize ordinary customer or staff
   accounts implicitly. Enable sandbox notifications and purchases only while this
   controlled production-profile test is required.
   Run `.venv/bin/python manage.py check_apple_billing_readiness --scenario all`
   before activation. Add `--require-enabled` only after changing the four Apple
   feature flags, and `--require-reconciliation` when validating the private API
   credentials. The command reads configuration and catalog state without making
   purchases or changing entitlements.
6. Enable notifications first. Confirm invalid JWS rejection, notification replay
   idempotency and lifecycle projection. Run
   `.venv/bin/python manage.py reconcile_apple_subscriptions --dry-run`.
7. In a development/TestFlight build on a physical iPhone, buy and restore each
   product with a sandbox tester. Confirm localized StoreKit pricing, matching
   `appAccountToken`, server verification before finish and renewal/expiration/
   grace/revocation behavior.
8. Enable production purchases only after that evidence passes. Remove or expire
   the sandbox authorization after validation and confirm no active sandbox entitlement
   remains. A simultaneous active Apple
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

Disable the provider flags. Do not delete subscriptions, payments, events,
Apple/Google account tokens or tax documents. Reconcile external state before
re-enabling.

## Google Play staging and lifecycle gate

Keep the existing `myscoope_basic` and `myscoope_pro` subscriptions and their
monthly/annual base plans, plus the three `myscoope.credits.*` one-time products;
do not duplicate product IDs. A purchase changes entitlements only after the
Google Play Developer API verifies its token and account binding.

Before the next Android build:

1. Set `BILLING_GOOGLE_PLAY_ENVIRONMENT=sandbox` in staging and keep production
   at `live`. Confirm that only the configured environment's four base plans
   and three credit packs are returned by `/api/v1/subscriptions`.
2. Give the existing Google Play API service account only the Android Publisher
   access needed to read purchases. Keep its JSON key in the secret file; never
   place it in Pub/Sub configuration or source control.
3. Create one Pub/Sub topic for the Play Console notifications and grant
   `google-play-developer-notifications@system.gserviceaccount.com` Publisher
   access. Select that topic in Play Console.
4. Create an authenticated push subscription targeting
   `/billing/webhooks/google-play/`. Use a dedicated push-auth service account,
   the exact configured `BILLING_GOOGLE_PLAY_PUBSUB_AUDIENCE`, and grant the
   Pub/Sub service agent permission to mint its OIDC token. Configure the same
   service-account email in
   `BILLING_GOOGLE_PLAY_PUBSUB_SERVICE_ACCOUNT_EMAIL`.
5. Keep `BILLING_GOOGLE_PLAY_RTDN_ENABLED=false` until the Play Console test
   notification is received with a valid JWT. Invalid audience, issuer, email,
   package or environment must be rejected without creating an inbox row.
6. Enable RTDN, repeat the test notification, then exercise one subscription
   and one credit pack. Confirm one idempotent `BillingEvent` per Pub/Sub
   `messageId`; the row must contain no raw purchase token. Provider/API failure
   must leave the event `failed` and return a retryable non-2xx response.

The Android client already follows the required completion order: it sends the
purchase token to My Scoope, waits for server verification and only then calls
`finishTransaction`. With `expo-iap` 5.5.1, subscriptions are acknowledged and
credit packs use `isConsumable=true`, which consumes the token so the product
can be bought again. Preserve this order in every client change.

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
