# CI Stabilization & Test Hygiene — QA Closure

Status: completed
Date: 2026-07-07
Cycle: CI00–CI05
Branch validated: `staging`

## Scope validated

This QA closure records the stabilization cycle that turned GitHub Actions into the
trusted quality gate for My Scoope staging.

The objective was not to change product behavior to satisfy outdated tests. The
objective was to make the automated suite reflect the current architecture and to
separate real regressions from obsolete expectations.

## Outcome

The full Django checks and tests workflow passed green on GitHub Actions after the
CI00–CI05 corrective cycle.

This means `staging` can now be treated as the integration branch that must remain
healthy before opening or reopening a pull request to production.

## What was corrected

### CI00/CI01 — onboarding gate and test scope

The nutrition onboarding gate was valid product behavior, but it made historical
tests receive redirects when they were not testing onboarding. The CI/test scope was
adjusted so non-onboarding tests do not become coupled to that gate.

Stable contract:

```text
Onboarding gate protects product flows.
Tests that are not about onboarding must opt out explicitly or run under CI settings
that keep the historical suite deterministic.
```

### CI02 — moved docs and historical contracts

Several tests still read documentation from old architecture paths even after the
documentation strategy moved active contracts into `docs/current/`, decisions into
`docs/decisions/`, and old context into `docs/archive/`.

Stable contract:

```text
Tests may validate documentation, but they must point to current source-of-truth
documents or explicitly state that they are validating history.
```

### CI03 — current proposal and picker contracts

Older tests expected proposal states and picker payloads that no longer represented
the current product. They were aligned with the current contracts:

```text
proposal review -> applicable -> applied
food picker -> enriched payload with metadata
AI iteration -> traced revision/command, not silent mutation
```

Stable contract:

```text
Tests defend current product contracts, not the implementation details of previous
cycles.
```

### CI04 — AI intake iteration tests

The remaining AI intake tests were too coupled to a fragile end-to-end setup. They
were narrowed so unit-level behavior and integration-level behavior are checked at
the right level.

Stable contract:

```text
A test should be as small as possible while still protecting the intended contract.
```

### CI05 — AI rate limits in CI

The final failure came from AI rate limits interacting with the full test suite order.
Rate limits remain part of production safety, but CI must not become non-deterministic
because many tests call AI flows in the same process.

Stable contract:

```text
Rate limiting is product protection.
CI should use deterministic limits or explicit overrides when testing unrelated flows.
```

## QA meaning of a green CI

A green GitHub Actions run means:

- Django system checks pass in a clean environment.
- The full automated test suite passes outside the developer machine.
- `staging` is a safe branch for integration and web staging validation.
- Pull requests to `main` should only be opened or reopened from a green `staging`.

It does not mean:

- every possible product bug is impossible;
- manual QA is unnecessary;
- staging can be skipped;
- tests are frozen forever.

## Regression policy

When a future test fails, classify it before changing code:

```text
1. Product regression: fix product code.
2. Obsolete expectation: update the test to the current documented contract.
3. Fragile UI assertion: prefer stable attributes or meaningful contract checks.
4. Configuration mismatch: adjust CI/test settings, not production behavior.
5. Fixture/setup issue: improve factories or setup data.
```

## Closure statement

CI00–CI05 closes the first CI stabilization and test hygiene cycle.

From this point forward, My Scoope should treat the automated suite as a living
quality contract. The suite must evolve with product decisions, and product decisions
must update tests when they intentionally change behavior.
