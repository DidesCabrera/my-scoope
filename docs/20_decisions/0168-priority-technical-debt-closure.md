# Decision 0168: Priority technical debt cycle closure

Date: 2026-08-02
Status: completed
Cycle: TDG09-TDG14

## Context

Decision 0167 authorized the remaining high-priority technical-debt work plus
the approved Nutrition Solver and account-plan transitions. The closure had to
preserve Food Catalog's strategic operational scope and product behavior while
turning the remaining migration assumptions into executable contracts.

## Completed outcomes

- `ExternalLLMOrchestrator` remains the stable facade, while provider-turn
  coordination and tool-selection policy now have dedicated application modules.
- AI/product integration is inverted through bindings owned by `ai_assistant` and
  registered by `notas`; production imports from `ai_assistant` to `notas` fell
  from 22 to zero and the dependency ratchet now enforces zero.
- Prepared-action persistence and product dispatch live behind the same explicit
  product port instead of leaking product ORM/command ownership into AI.
- CI no longer duplicates a staging push and its pull-request workflow. Proposed
  changes run from `pull_request`; protected branch results run from `push`.
- Browser CI creates deterministic disposable data, runs the full anonymous and
  authenticated suite, and reuses in-memory authentication without storing secrets
  or browser state files.
- The four `notas.application.nutrition_engine` compatibility bridges were removed
  after their final production consumer migrated to direct `nutrition_solver`
  imports.
- Migration `notas.0045` copies historical `Profile.plan` capabilities into
  accounts-owned plans/subscriptions before removing the field, and restores the
  legacy assignment on reverse migration.
- Commercial entitlement and AI-credit resolution now use accounts-owned plans
  without runtime fallback to `Profile.plan`.

## Closure evidence

- Django fast structural gate: 80 tests passed.
- Complete Django suite: 1,649 tests passed in 262.519 seconds.
- AI Assistant suite: 220 tests passed.
- Account/migration/solver/E2E-seed focused suite: 55 tests passed.
- MCP contract/protocol suite: 169 tests passed.
- Browser suite: 27 authenticated and anonymous scenarios passed in 35.44 seconds
  against a freshly migrated disposable SQLite database.
- Ruff fatal correctness gate and dependency vulnerability audit: passed.
- Django checks, migration drift, repository hygiene, frontend budgets, browser
  contract and document registry: passed.
- Repository search: zero production AI→`notas` imports, zero retired solver bridge
  imports and zero `Profile.plan` runtime consumers.

## Consequences

The three registered transitions `ai-product-adapter-boundary`,
`nutrition-solver-legacy-import-bridges` and `legacy-account-plan-fallback` are
closed and removed from the current transition registry. Historical decisions and
migrations remain available for audit and rollback.

Food Catalog remains intentionally broad inside Admin Operations. No part of this
closure reduces its strategic or operational responsibility.
