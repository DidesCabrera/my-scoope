# 0080 · CI stabilization and test hygiene

Date: 2026-07-07
Status: accepted
Cycle: CI00–CI05
Related docs:

```text
docs/current/qa/ci_stabilization_qa.md
docs/current/operations/testing_and_ci_policy.md
```

## Context

After enabling GitHub Actions as a real quality gate for `staging`, the full Django
suite exposed accumulated test debt. The failures were not one single product bug.
They were a mix of:

- tests coupled to old onboarding assumptions;
- documentation tests pointing to moved documents;
- proposal tests expecting pre-current review/apply states;
- picker tests expecting old payload shapes;
- CI determinism issues caused by rate limits;
- tests that were too end-to-end for the contract they intended to protect.

The first full runs were noisy, but each corrective patch reduced the failure surface
until the suite passed green.

## Decision

Adopt CI stabilization and test hygiene as a formal project policy.

My Scoope will treat GitHub Actions as the external quality gate for `staging` and
pull requests. Tests must protect current product contracts, not historical behavior
that has been superseded by accepted decisions.

When a test fails, the project must classify the failure before changing production
code:

```text
product regression
obsolete expectation
fragile assertion
configuration mismatch
fixture/setup issue
```

## Accepted contracts

### 1. Staging must return to green

`staging` is allowed to receive integration commits, but it should return to a green
GitHub Actions state before being used as the source for production merge.

### 2. Tests evolve with contracts

When a patch intentionally changes a product contract, the same cycle must update
the related tests and documentation.

### 3. CI overrides must be explicit

CI may disable or raise limits that make the suite non-deterministic, but only when
the product protection remains active outside CI.

Examples:

```text
onboarding gates
AI rate limits
feature flags
credit/pricing guardrails
```

### 4. Documentation tests should follow the docs architecture

Tests should prefer current source-of-truth documents:

```text
docs/current/
docs/decisions/
```

Archived documents may be referenced only when the test is explicitly historical.

### 5. Product code should not regress to satisfy obsolete tests

If a test defends behavior that has been replaced by a documented current contract,
the test must be updated. Production code should not be changed just to satisfy an
obsolete expectation.

## Consequences

Positive:

- `staging` now has a clean quality gate.
- Future pull requests can be reviewed with more confidence.
- Test failures have a decision framework.
- The project has a documented policy for keeping tests useful instead of burdensome.

Tradeoffs:

- Some patches must include test and documentation updates, not only product code.
- CI may require periodic hygiene as architecture evolves.
- Old tests must be reviewed rather than blindly preserved.

## Follow-up work

Recommended preventive improvements:

```text
1. Introduce common test factories/helpers for users, wallets, proposals and nutrition entities.
2. Add data-testid attributes for UI elements that are stable product affordances.
3. Split fast focused CI from full PR CI if execution time becomes a bottleneck.
4. Keep documentation tests pointed at current source-of-truth documents.
5. Add a lightweight CI troubleshooting guide for future contributors/AI sessions.
```

## Summary

CI00–CI05 marks the transition from feature expansion with partial validation to a
staging workflow protected by a full automated quality gate.

The suite is now part of the product's operating system.
