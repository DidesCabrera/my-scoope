# 0051 · Account plans and credits domain

Status: accepted  
Date: 2026-07-04

## Context

My Scoope already has several pieces related to user access and AI economics:

```text
accounts
  -> account/onboarding flow

notas.Plan and notas.Profile.plan
  -> current legacy membership/permission model

ai_assistant.AIUsageEvent
  -> operational usage, tokens, estimated cost and status

ai_assistant.AIUserCreditQuota / AICreditLedger
  -> first AI-credit layer by membership
```

This was useful to activate the AI Assistant safely, but the commercial responsibility is now becoming broader than AI execution.

Plans, subscriptions, entitlements and user-visible credits are account-level responsibilities. They should not remain owned by `notas`, whose main responsibility is the nutrition/product domain, nor by `ai_assistant`, whose main responsibility is AI execution, tool orchestration and usage observability.

## Decision

`accounts` becomes the target domain owner for commercial account capabilities:

```text
AccountPlan
AccountSubscription
CreditWallet
CreditLedger
commercial entitlements
plan state
credit balance
credit reservation/consumption/refund
```

Tokens remain an internal provider-cost metric. Users should interact with credits, not tokens.

`notas.Plan` is considered a legacy/transitional model for the current permission system. It must not be removed abruptly.

The existing `ai_assistant` credit implementation remains valid as a transitional AI-specific implementation, but future credit ownership should move toward `accounts` and be consumed by AI Assistant through application services.

## Consequences

- New commercial plan work should happen in `accounts`, not in `notas`.
- `notas` may keep nutrition/product entities and compatibility with existing `Profile.plan` references.
- `ai_assistant` should keep recording operational details such as tokens, provider/model, estimated USD cost, status and `action_type`.
- Credits visible to users should be resolved through `accounts` over time.
- The migration must use adapters/fallbacks before deprecating `notas.Plan`.
- Billing provider integration is intentionally out of scope for the first ACC cycle.

## Implementation plan

The implementation will be tracked in:

```text
docs/planning/account_plans_credits_cycle.md
```

Initial cycle:

```text
ACC00 — Docs: Account Plans + Credits strategy
ACC01 — AccountPlan / AccountSubscription base
ACC02 — CreditWallet / CreditLedger
ACC03 — Seed de planes comerciales
ACC04 — Integración con AI Assistant: estimar/reservar créditos
ACC05 — Registro real de AIUsageEvent
ACC06 — Profile/Admin UI: mostrar plan y créditos
ACC07 — Migración gradual desde notas.Plan hacia account entitlements
```
