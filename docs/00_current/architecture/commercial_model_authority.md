# Commercial model authority

## Current source of truth

All new product, mobile, admin and analytics consumers must enter commercial
state through `accounts` services and models:

| Concern | Authority | Non-authoritative evidence/compatibility |
| --- | --- | --- |
| Plan and entitlements | `accounts.AccountPlan` | `notas.Plan` historical only |
| User subscription state | `accounts.AccountSubscription` | `billing.ProviderSubscription` provider evidence |
| Credit balance and movements | `accounts.CreditWallet`, `accounts.CreditLedger` | AI credit models are transitional |
| AI provider cost and usage | `ai_assistant.AIUsageEvent` | Never a balance authority |
| Nutrition profile | `notas.Profile` | Not a commercial profile |
| Nutritionist/member relationship | `notas.NutritionistMemberRelationship` | Proxy over legacy `notas.Subscription`; not a paid subscription |

Provider subscription updates must pass through
`billing.application.services.projections.project_provider_subscription` before
they affect entitlements. AI usage may correlate to account-ledger references,
but it must not create a second commercial balance.

Operational checks:

```bash
python manage.py reconcile_legacy_ai_credits --period YYYY-MM --fail-on-difference
python manage.py reconcile_legacy_ai_credits --period YYYY-MM --require-legacy-parity
```

The first command is the durable post-cutover integrity gate: account AI
consumption must match charged usage events. The second is only for a pre-cutover
snapshot because frozen legacy rows intentionally stop changing afterwards.

## Active transitions

The remaining compatibility surfaces and their exit evidence live in
`docs/00_current/architecture/transition_registry.json`. The authoritative
cutover decision is `docs/20_decisions/0170-commercial-model-authority-and-cutover.md`.
