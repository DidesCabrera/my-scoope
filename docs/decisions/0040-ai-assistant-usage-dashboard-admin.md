# 0040 · AI Assistant usage dashboard/admin

Status: accepted
Date: 2026-07-02

## Context

Patch 56 started persisting usage observability in `AIUsageEvent`. Patch 57 added technical guardrails. Patch 58 connected `llm_preview` to the existing chat surface. Patch 59 introduced AI credits as the commercial usage unit behind an explicit feature flag.

The next operational need is not another product-facing AI feature. The next need is an internal admin/reporting surface that lets My Scoope understand real usage before broad activation:

```text
usuario
  -> action_type
  -> provider/model
  -> tokens/costo interno
  -> créditos cobrados
  -> bloqueo/error
  -> cuota mensual
```

This keeps the cost-control cycle grounded in observed behavior rather than assumed pricing.

## Decision

Add an internal AI Assistant usage dashboard in Django Admin, backed by an application report builder.

The report aggregates usage by:

```text
period
status
user
action_type
provider/model
credit_plan_code
quota pressure
recent events
```

The dashboard is intentionally admin-only. Tokens and USD estimates remain internal observability details. The commercial unit exposed to memberships remains AI credits.

## Implementation

Patch 60 introduces:

```text
ai_assistant/application/reports.py
ai_assistant/templates/admin/ai_assistant/aiusageevent/change_list.html
ai_assistant/templates/admin/ai_assistant/aiusageevent/usage_dashboard.html
ai_assistant/tests/test_usage_dashboard.py
```

`AIUsageEventAdmin` gets a custom `usage-dashboard/` admin URL and a link from the changelist.

The report builder is independent from the template so it can later be reused by:

```text
management commands
staff dashboards
scheduled cost summaries
CSV exports
```

## Non-goals

Patch 60 does not:

- expose AI usage/costs to end users;
- change membership billing;
- enable credits enforcement by default;
- add charts or a public dashboard;
- change provider pricing assumptions.

## Consequences

My Scoope can now inspect real cost drivers before scaling the AI Assistant:

```text
costo por función
costo por modelo
usuarios de alto uso
bloqueos por guardrails/créditos
errores del provider
créditos cobrados por periodo
presión de cuota mensual
```

The next cycle can focus on cost optimization using these observed aggregates.
