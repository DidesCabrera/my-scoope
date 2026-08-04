# 0170 · Commercial model authority and cutover

Status: accepted
Date: 2026-08-03

## Context

The ACC cycle created the target account models but left parallel historical
models and active readers/writers in place. Calling the migration complete while
both credit ledgers remain active makes the source of truth ambiguous.

## Decision

The ownership contract is:

```text
accounts.AccountPlan
  -> commercial plan and entitlements authority

accounts.AccountSubscription
  -> user entitlement/subscription authority

accounts.CreditWallet + accounts.CreditLedger
  -> commercial balance and movement authority

billing.ProviderSubscription
  -> provider-side evidence only; projected into AccountSubscription

ai_assistant.AIUsageEvent
  -> provider/model/token/cost/status evidence and correlation only
```

The similarly named `notas` models do not form a parallel commercial domain:

- `notas.Profile` is the nutrition/user profile;
- `notas.Subscription` is a nutritionist/member relationship and needs a clearer
  public name in its own compatibility patch;
- `notas.Plan` is historical data and must not receive new consumers.

`AIUserCreditQuota` and `AICreditLedger` are explicitly transitional and frozen.
Runtime, operations and analytics use account-owned projections. Only the
read-only historical Admin and `reconcile_legacy_ai_credits` boundary may read
them; an executable regression test rejects any new production consumer.

## Cutover sequence

1. Add account-owned quota/blocked-state projections needed by operations.
2. Reconcile AI ledger totals and usage-event references against account ledger
   entries, recording discrepancies without silently correcting history.
3. Compare legacy parity explicitly before cutover; after cutover, divergence is
   expected and is reported as informational.
4. Switch runtime, Admin Operations, Admin Analytics, reports and provider
   validation to account services.
5. Stop legacy AI credit writes for one release and monitor. Carry the latest
   per-user legacy operational block into `CreditWallet` with a data migration.
6. Remove legacy models/tables in a later reversible migration.

The transition registry keeps both compatibility boundaries visible until this
evidence exists. Documentation status must not claim the cutover is complete
before the registry entries can be removed. The nutritionist/member relation is
now exposed as `NutritionistMemberRelationship`, a zero-copy proxy over the
legacy `Subscription` table; new code must use the unambiguous name.
