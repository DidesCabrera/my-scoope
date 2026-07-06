# 0057 · Admin Analytics AI Assistant metrics

Status: accepted
Date: 2026-07-04

## Context

ADM04 extends `admin_analytics` from executive and commercial metrics into AI
Assistant operations. My Scoope already records `AIUsageEvent`, transitional
`AIUserCreditQuota` / `AICreditLedger`, and AI proposal outcomes. Those records
are enough for a first read-only operational dashboard without adding analytics
snapshots.

## Decision

Add a staff-only AI Assistant Analytics page at:

```text
/staff/analytics/ai-assistant/
```

The page reads existing data through `admin_analytics` selectors/services and
presents:

```text
usage volume and status
active AI users
tokens and cached tokens
estimated internal USD cost
average cost per completed turn
latency
charged AI credits
AI credit ledger and quota pressure
action_type ranking
provider/model ranking
credit_plan_code grouping
top users by cost/tokens/credits
AI proposals and AI chat outcomes
```

The page keeps tokens and USD cost as internal observability only. User-facing
pricing remains credit-based.

## Consequences

`admin_analytics` now consumes `ai_assistant` operational data but does not own or
mutate it.

ADM04 does not add models or migrations. It remains read-only and staff-only.

Tool-level visibility is initially limited by the data already persisted in
`AIUsageEvent`: the dashboard can show `tool_calls_count` and action types, but
not a reliable per-tool-name ranking until tool names are explicitly persisted in
future usage metadata.
