# 0062 · Admin Analytics internal alerts / health signals

Status: accepted
Date: 2026-07-04

## Context

ADM02-ADM08 created read-only analytics screens for overview, accounts, AI
Assistant, product activity, Food Catalog, Nutrition Solver and shared filters.
The next need is not a new data source, but a consolidated internal layer that
surfaces operational risk quickly.

## Decision

Add an `Alerts` section inside `admin_analytics` at:

```text
/staff/analytics/alerts/
```

The page derives alerts from existing selectors and metrics. It does not create
new models, snapshots, tasks or mutable workflows.

## Scope

ADM09 introduces alert groups for:

```text
critical
warning
watch
info
```

The first alert set observes:

```text
Product Activity
AI Assistant
Accounts
Food Catalog
Nutrition Solver
```

Examples:

```text
AI error rate elevated
AI quota hard blocks present
credits reserved in wallets
Food Catalog quality/evidence risk
Nutrition Solver partial/impossible ratio
low Weekly Active Nutrition Builders
```

## Consequences

- `admin_analytics` remains read-only.
- Alerts are computed live from existing metrics.
- No migration is required.
- Historical alert snapshots can be considered later only if operational review
  needs trend history.
