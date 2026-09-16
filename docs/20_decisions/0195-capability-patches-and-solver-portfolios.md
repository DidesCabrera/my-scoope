# Decision 0195: capability patches and solver portfolios

Status: accepted
Date: 2026-09-16

## Context

The assistant reached broad product coverage by adding bounded read tools and one
prepared-action entry point for each supported mutation. That made permissions and
confirmation safe, but it also made the model reason in terms of micro-tools. At the
same time, Optimization V2 could compute distinct solutions but proposal review only
consumed one of them. The solver was therefore present as a generator, not yet as an
iterative collaborator.

Modern models can understand a larger user objective, but that does not make browser
automation or direct ORM access an acceptable product boundary. UI automation is
useful for an external operator, while an embedded assistant needs stable ownership,
validation, atomicity, audit and approval semantics.

## Decision

The provider-facing mutation boundary is capability-oriented. The model prepares one
`ai_assistant_workspace_patch.v1` document through `propose_workspace_patch`. A patch
contains up to twenty-four ordered operations over supported product resources. My Scoope,
not the model, maps each operation to an existing application command, verifies
ownership and arguments, captures a before/after preview and classifies aggregate
risk.

An operation may reference the typed entity ID produced by an earlier create operation
inside the same patch. References are backward-only, type-checked and limited to
allowlisted target or relation ID fields. This supports atomic create-and-compose
flows without exposing arbitrary result paths or provider-authored database access.

Patch preparation never mutates the target entities. The trusted web or mobile UI is
the only commit entry point. Commit locks the prepared action, revalidates every target
fingerprint and executes all operations in one database transaction. A stale or
invalid operation aborts the complete patch. The earlier `prepare_product_action`
contract remains registered for compatibility but is no longer selected for new
provider turns.

The approval policy is explicit:

- low risk: create, rename and bounded updates;
- medium risk: lifecycle transitions with material effects, including applying a
  proposal;
- high risk: delete, reject, cancel and destructive week removal;
- version 1 requires trusted confirmation for every risk level. Low-risk patches only
  expose `future_auto_apply_eligible`; that metadata is not permission and does not
  auto-commit anything.

Daily-plan optimization becomes portfolio-oriented. The default `portfolio_v1`
adapter asks deterministic CP-SAT for three distinct alternatives, ranks them by
nutritional quality, functional quality and objective, stores their complete trusted
payloads with the proposal, and selects the best as the initial review payload. The
user may choose another stored alternative before approval; the server validates and
simulates it again.

The optimizer now:

- normalizes nutrient deviations relative to each preferred target so kcal cannot
  dominate merely because of its numeric unit;
- distinguishes the mathematical solver status from product quality status;
- applies typed dietary/allergen constraints when declared;
- incorporates preparation effort, cost, simplicity, meal affinity and variety;
- records quality deltas between consecutive assistant-driven proposal revisions.

`portfolio_v1` falls back to the legacy generator only when CP-SAT cannot produce a
feasible portfolio or the operational food snapshots are insufficient and no typed
dietary/allergen safety constraint was declared. Safety-constrained requests fail
closed instead of entering the legacy path. The fallback reason is persisted.
Explicit `cp_sat_v1` remains fail-closed, while
`heuristic_v2` remains the configuration rollback.

## Consequences

- The assistant reasons about a user outcome and emits one patch instead of planning a
  chain of micro-tools.
- Application commands, ownership checks and trusted confirmation remain the authority;
  model intelligence does not bypass them.
- A proposal can carry several alternatives without duplicating proposal records.
- Solver iteration has comparable evidence instead of only a new payload.
- Dietary safety depends on typed operational snapshots. Declared allergies fail safe
  for candidates whose allergen capability is unknown.
- The patch vocabulary is intentionally bounded to supported domain commands. Food
  composition inside Meals and Meal snapshots inside DailyPlans are supported;
  Program day composition, sharing, imports, billing and staff operations still need
  dedicated domain adapters before they may enter the generic patch.

This decision supersedes the provider-facing micro-tool preference in 0155 and the
inactive-alternatives posture in 0147/0149. Their ownership, review and rollback
constraints remain in force.
