# 0073 · Admin Operations Food Catalog workflow

Status: accepted  
Date: 2026-07-04  
Related cycle: `admin_operations` OPS03

## Context

OPS01 created the independent `admin_operations` shell and OPS02 added the first
read/action overview. The first workflow that should become actionable is Food
Catalog because the project already has explicit curation models and service
boundaries:

```text
CatalogCurationCandidate
CatalogFood
food_catalog.application.curation.transition_catalog_food_status
```

The operational console should help staff resolve real catalog queues without
turning `admin_analytics` into a mutation surface and without replacing Django
Admin as a raw technical editor.

## Decision

Add `/staff/operations/food-catalog/` as the first domain-specific Admin
Operations workflow.

The workflow exposes two operational queues:

```text
1. CatalogCurationCandidate records in queued / in_review / needs_more_evidence.
2. CatalogFood records in candidate / normalized / pending_review / needs_more_evidence states.
```

Candidate actions are handled inside `admin_operations.services` and require a
reason before mutation. The action stores an operational note on the candidate
with actor, previous status, new status and reason. This is intentionally a
bridge until OPS06 introduces a formal audit model.

CatalogFood actions use the existing Food Catalog curation service:

```text
transition_catalog_food_status(...)
```

This protects the status workflow and publication guards already defined in the
Food Catalog domain.

## Consequences

- `admin_analytics` remains read-first.
- `admin_operations` now has its first real action queue.
- The Food Catalog navigation item is enabled in the operational shell.
- Candidate interventions require a staff reason and leave local context in
  `CatalogCurationCandidate.notes`.
- CatalogFood interventions reuse the existing domain transition service.
- No migration is required for OPS03.
- OPS06 should still introduce a formal operations audit log before financial,
  blocking or destructive workflows expand.

## Non-goals

OPS03 does not create `CatalogFood` from candidates automatically.

OPS03 does not write `notas.Food`, does not publish snapshots and does not touch
solver-facing operational foods.

OPS03 does not replace Django Admin for raw field editing.
