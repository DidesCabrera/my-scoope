# 0072 · Admin Operations operational overview

Date: 2026-07-04
Status: accepted
Related planning: `docs/planning/admin_operations_console_cycle.md`
Related decisions:

```text
0070 · Admin Operations Console planning
0071 · Admin Operations app shell
```

## Decision

Implement OPS02 by turning `/staff/operations/` into the first read/action overview for
Admin Operations.

The page now shows operational queues derived from real domain models when available:

```text
- Food Catalog curation candidates and master foods requiring review.
- AI Assistant usage events with errors/blocks and AI/MCP proposals pending review.
- Accounts wallets with reserved credits.
- Audit Log as a planned queue until OPS06 introduces the audit foundation.
```

## Rationale

OPS02 should not add mutations yet. Its purpose is to prove the console can aggregate
work queues across domains without becoming a strategic dashboard or a raw CRUD surface.

This keeps the operating rule intact:

```text
admin_analytics detects what is happening.
admin_operations prioritizes what staff can resolve.
Domain-specific patches add the actual actions.
```

## Scope included

```text
- Add selectors for detectable operational queues.
- Add viewmodels for metrics, queues and warnings.
- Render KPI cards, queue cards and operational warnings in the overview.
- Keep all queue actions disabled until their workflow patches ship.
- Add tests for live counts and staff-only rendering.
```

## Scope excluded

```text
- No approve/reject Food Catalog workflow yet.
- No credit adjustment or reservation release yet.
- No AI proposal mutation workflow yet.
- No operations audit model yet.
- No cross-links from Admin Analytics yet.
```

## Migration note

OPS02 creates no models and requires no migration.
