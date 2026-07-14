# 0075 · Admin Operations AI Assistant workflow

Date: 2026-07-04
Status: implemented
Cycle: Admin Operations Console
Patch: OPS05

## Context

OPS02 exposed AI operational signals but kept the action disabled: recent `AIUsageEvent` errors/blocks, AI/MCP `NutritionProposal` records pending review and quota records that can explain blocked access.

OPS05 converts those signals into a guided staff-only workflow without turning `admin_analytics` into a mutation surface.

## Decision

Enable `/staff/operations/ai-assistant/` as the AI Assistant operational workflow.

The workflow supports three bounded interventions:

```text
- acknowledge/escalate recent AIUsageEvent errors or blocks by writing review metadata;
- approve/reject AI/MCP NutritionProposal records with reason and proposal audit event;
- block/unblock AI access through AIUserCreditQuota.hard_blocked when the quota model supports it.
```

## Implementation notes

```text
- AIUsageEvent status is not rewritten; staff review state is stored in metadata.admin_operations.
- Proposal review uses explicit status transitions and writes NutritionProposalAuditEvent with OPS05 metadata.
- Quota block/unblock writes AIUserCreditQuota.hard_blocked and appends a zero-credit AICreditLedger adjustment as operational trace.
- Every mutation requires a reason.
- Overview now links the AI Assistant queue to the workflow.
```

## Boundary

OPS05 does not run LLM tools, apply proposals to DailyPlans or change AI usage economics. It only reviews operational records and toggles the existing quota hard-block flag.

A formal unified `AdminOperationAuditEvent` remains scheduled for OPS06.

## Migration

No migration required.
