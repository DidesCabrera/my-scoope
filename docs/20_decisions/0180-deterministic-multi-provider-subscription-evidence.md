# 0180 - Deterministic multi-provider subscription evidence

Status: accepted
Date: 2026-08-05

## Decision

`accounts.AccountSubscription` remains the single effective commercial state for
one My Scoope account. Apple App Store and Mercado Pago retain independent,
provider-authenticated evidence in `billing.ProviderSubscription`; neither
provider becomes a second entitlement authority.

Every verified provider change recomputes the projection from all stored
evidence. Active evidence wins over inactive evidence, then the higher
`AccountPlan.display_order`, later period end, explicit inactive-state priority,
stable provider priority and row identity break ties. The projection records all
participating evidence and whether more than one provider is active. It never
silently cancels or deletes a duplicate active channel.

Apple uses StoreKit 2 and App Store Server API signed data. A stable,
account-owned UUID is passed as `appAccountToken`; the server verifies signature,
bundle, environment, account token and configured product mapping before it
updates evidence. The client finishes a transaction only after this server
acceptance. App Store Server Notifications V2 enter the idempotent billing inbox
only after signature verification, and reconciliation can refresh every stored
original transaction ID from Apple's server API.

Only active `BillingProduct` mappings determine which Apple product identifiers
the consumer client may request. Localized price and currency come from StoreKit,
not from hard-coded app or API values. CML06 does not create a product identifier,
price or plan on behalf of the owner.

## Consequences

- Consumer-member accounts may purchase and restore in the iOS app;
  nutritionist and invited-member purchasing remain outside the mobile MVP.
- Unknown account tokens, unmapped products and family-shared transactions fail
  closed. Existing evidence is retained for lifecycle and account-deletion audit.
- Grace period preserves access; billing retry becomes past due; expiration and
  revocation remove active access without erasing provider evidence.
- Admin Operations reports simultaneous active providers as a possible double
  charge requiring review.
- Repository completion does not claim App Store Connect configuration or a
  sandbox purchase. Product creation, notification URL registration, agreements,
  tax/banking setup and physical-device sandbox proof remain external gates.
