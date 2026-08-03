# Decision 0167: Priority technical debt closure

Date: 2026-08-02
Status: accepted
Cycle: TDG09-TDG14

## Context

TDG00-TDG08 established quality surfaces and reduced the largest structural
hotspots. The remaining high-priority work is now narrow enough to close: provider
turn coordination still dominates the AI facade, product executors import `notas`,
authenticated browser coverage is not CI-owned, and CI duplicates work for staging
PRs. Two approved transitional bridges also remain in the solver and account plan
boundaries.

## Decision

Execute TDG09-TDG14 as one behavior-preserving closure cycle:

- keep `ExternalLLMOrchestrator` as the stable facade while extracting provider-turn
  coordination and tool-selection policy;
- invert AI/product coupling through ports owned by `ai_assistant` and registrations
  performed by the product side;
- seed deterministic, disposable authenticated browser fixtures in CI;
- run proposed changes from the pull-request event and protected branch results from
  push events, avoiding duplicate staging executions;
- retire `notas.application.nutrition_engine` re-export bridges after migrating the
  last production consumer;
- migrate `Profile.plan` capabilities into accounts-owned records reversibly, then
  remove the field and all fallback resolution.

## Consequences

The AI boundary can be tested with injected dispatch tables without importing the
product implementation. Product composition remains explicit in Django startup.
Authenticated E2E becomes reproducible without committed real credentials or fixed
database IDs. Account entitlements have one authority, and solver imports reflect
their true owner.

Food Catalog remains intentionally large where its operational workflows require it;
this decision does not reduce that domain.
