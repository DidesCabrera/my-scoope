# 0076 · Admin Operations audit log foundation

Status: accepted
Date: 2026-07-04
Cycle: Admin Operations Console · OPS06

## Context

OPS03, OPS04 and OPS05 introduced real staff-only mutations in `admin_operations`:
Food Catalog curation actions, account credit interventions and AI/proposal operations.
Each workflow wrote useful local traces, but the operational console still lacked one
cross-domain audit surface.

The product boundary requires a formal answer to:

```text
Who acted, on what entity, what changed, why, and when?
```

## Decision

Create a dedicated append-only model in `admin_operations`:

```text
AdminOperationAuditEvent
```

The model stores:

```text
actor
actor_label
action
source
target_app
target_model
target_id
target_label
status_before
status_after
reason
metadata
created_at
```

Targets are stored as plain app/model/id fields instead of a generic foreign key. This is
intentional: Admin Operations crosses domain boundaries and the audit trail should remain
readable even if a target model moves, is renamed or is deleted in a future refactor.

## Consequences

- OPS06 requires a migration.
- The audit event is append-only: updates and deletes are blocked at model level.
- Existing domain logs remain valid:
  - `CreditLedger` continues to be the financial ledger.
  - `NutritionProposalAuditEvent` continues to be the proposal-domain audit trail.
  - `AIUsageEvent.metadata.admin_operations` continues to carry event review state.
- `AdminOperationAuditEvent` becomes the transversal staff-action log.
- `/staff/operations/audit-log/` is enabled as a staff-only screen.

## Implementation notes

OPS06 wires audit writes into the mutations introduced in OPS03-OPS05:

```text
- Food Catalog candidate actions
- CatalogFood status transitions
- Credit wallet manual adjustments
- Credit reservation releases
- AI usage event acknowledge/escalate
- AI quota block/unblock
- AI/MCP proposal approve/reject
```

Every audit write includes the required reason and a status transition or state summary.

## Non-goals

OPS06 does not add fine-grained staff roles. The console remains protected by `is_staff`.

OPS06 does not replace Django Admin history, financial ledgers, AI usage records or proposal
audit events. It consolidates operational staff actions in one product-facing internal log.
