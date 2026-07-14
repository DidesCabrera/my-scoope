# 0056 · Admin Analytics account metrics

Status: accepted
Date: 2026-07-04

## Context

ADM02 created the executive overview for `admin_analytics`, including a small
summary of subscriptions, wallets and credit consumption.

The next step in the Admin Analytics cycle is ADM03: a deeper commercial view
for the `accounts` domain. The product needs to observe plans, subscriptions,
wallet balances and append-only credit ledger movements without moving business
logic out of `accounts`.

## Decision

Add a dedicated staff-only page:

```text
/staff/analytics/accounts/
```

The page is read-only and consumes existing `accounts` tables:

```text
AccountPlan
AccountSubscription
CreditWallet
CreditLedger
```

The reporting structure follows the Admin Analytics boundary:

```text
admin_analytics/selectors/accounts.py
admin_analytics/services/accounts.py
admin_analytics/templates/admin_analytics/accounts.html
```

`accounts` remains the source of commercial truth. `admin_analytics` only reads,
aggregates and presents the information.

## Metrics included

Initial ADM03 metrics:

```text
plans total / active / draft / archived
plan credit configuration
active subscriptions by plan
subscription status counts
new subscriptions in 7/30 days
wallet total balance
wallet reserved balance
wallet available balance
wallets with reserved credits
largest wallet balances
credit ledger entries in 7/30 days
ledger deltas by kind
credits granted / consumed / reserved / released
```

## Consequences

- Admin Analytics now has an account-specific section beyond the executive
overview.
- No migrations are required.
- No commercial state is mutated.
- Future patches can add time filters, charts, cohort analysis or billing-provider
signals without coupling `accounts` to other domains.
