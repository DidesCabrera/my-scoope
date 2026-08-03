# Decision 0159: contain growth before broad structural decomposition

Date: 2026-08-02
Status: accepted
Cycle: TDG00-TDG08

## Context

My Scoope remains functionally healthy after rapid product growth, but several
quality surfaces and module boundaries did not grow at the same rate. The full
Django suite is green, while MCP and browser tests live outside the authoritative CI
gate. Admin Operations and AI Assistant concentrate orchestration in very large
modules, test data setup is duplicated, and frontend debt lacks executable no-growth
budgets.

The recent Food Catalog expansion inside Admin Operations is intentional. Food
Catalog has gained strategic and operational relevance, so reducing that capability
would solve the wrong problem.

## Decision

Run TDG00-TDG08 as a behavior-preserving debt cycle with this order:

1. consolidate the current feature baseline;
2. make every test surface reproducible and visible in CI;
3. add debt ratchets and dependency policies;
4. decompose Admin Operations and AI Assistant behind stable facades;
5. improve test setup and frontend containment;
6. close transitional debt only when its registered exit evidence is satisfied.

Food Catalog remains a primary Admin Operations responsibility. Its code will be
split by ownership, not removed or demoted.

## Consequences

- Structural changes must remain independently reviewable and test-backed.
- The complete Django suite stays authoritative for product regression confidence.
- MCP and browser surfaces gain explicit owners rather than being implied by the
  Django job.
- Temporary compatibility facades are acceptable during controlled splits, but new
  dependencies cannot be added without an executable policy update.
- Production rollout and Knowledge Center work remain outside this cycle.
