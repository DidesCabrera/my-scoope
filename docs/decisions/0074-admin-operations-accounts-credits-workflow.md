# 0074 · Admin Operations Accounts & Credits workflow

Date: 2026-07-04
Status: implemented
Cycle: Admin Operations Console
Patch: OPS04

## Context

Admin Operations needs a safe staff-only surface for account and credit interventions. Credits are commercial state and must not be edited silently through broad CRUD screens.

## Decision

Enable `/staff/operations/accounts/` as the guided Accounts & Credits workflow.

The workflow uses existing `CreditWallet` and append-only `CreditLedger` records. Manual adjustments and reservation releases require an explicit staff reason.

## Implementation notes

```text
- Account list/search surfaces wallets and open reservations.
- User detail exposes wallet facts, recent ledger entries and open reservations.
- Manual adjustments create CreditLedger.Kind.ADJUSTMENT.
- Reservation release reuses release_account_credit_reservation.
- The workflow prevents zero adjustments, negative balances and balance < reserved balance.
```

## Boundary

This patch does not introduce a formal cross-domain operations audit model. Until OPS06, staff actor context is stored in ledger metadata for financial actions.

## Migration

No migration required.
