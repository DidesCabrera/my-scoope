# Testing & CI Policy

Status: active
Date: 2026-07-07
Applies to: `staging`, pull requests, GitHub Actions, Django test suite

## Purpose

Tests in My Scoope exist to increase confidence and development speed. They should
protect current product contracts, domain rules and integration boundaries. They
should not preserve outdated behavior after a documented decision changes the
architecture.

## Branch policy

```text
local work -> staging -> GitHub Actions -> staging web QA -> PR to main -> production
```

`staging` is the integration branch. It may receive patches and corrective commits,
but it should return to green before being used as the source of a production pull
request.

`main` should only receive code from a green `staging` branch.

## Workflow policy

GitHub Actions is the external quality gate because it runs in a clean environment,
not on the developer machine.

Recommended levels:

```text
1. Local focused tests during patch work.
2. Full GitHub Actions run on push to staging.
3. Full GitHub Actions run on pull request to main.
```

A full green run is required before merging to `main`.

## Test categories

### Domain tests

Protect business rules and invariants.

Examples:

- a wallet cannot silently lose credits;
- a proposal cannot be applied twice;
- a private plan cannot be used by another user;
- a solver contract returns validated structures.

These tests are high value and should rarely be weakened.

### Integration tests

Protect important flows across apps.

Examples:

- AI Assistant generates a reviewable proposal;
- proposal application creates user-owned nutrition entities;
- credit charging records observable usage;
- Admin Operations mutates state with audit events.

These tests may need fixture updates when app boundaries move, but they should keep
protecting the product flow.

### UI/HTML tests

Protect meaningful user-facing affordances.

Use stable checks whenever possible. Prefer data attributes or structural contracts
over decorative copy when the exact text is not the product contract.

### Documentation tests

Protect source-of-truth documentation.

They should read from:

```text
docs/00_current/
docs/20_decisions/
```

They should not depend on `docs/90_archive/` unless the test explicitly validates
historical migration context.

### Configuration tests

Protect the difference between production safety and CI determinism.

Examples:

- onboarding gates;
- rate limits;
- AI credit limits;
- feature flags;
- environment-driven settings.

These tests must make the intended environment explicit.

## Test hygiene rules

Detailed guidance lives in `docs/40_technical/qa/testing_hygiene_guide.md`.

### 1. A failing test must be classified first

Do not immediately change product code. First decide whether the failure is:

```text
product regression
obsolete expectation
fragile assertion
configuration mismatch
fixture/setup issue
```

### 2. Tests must follow current contracts

When a patch changes a product contract, the patch must update related tests in the
same cycle.

Example:

```text
Old contract: approved/final proposal is directly apply-ready.
Current contract: applicable proposal becomes applied through an explicit command.
```

The test should protect the current contract.

### 3. CI settings must not weaken production settings

CI may override settings to make tests deterministic, but those overrides must be
explicit and scoped to CI or tests.

Examples:

```text
NUTRITION_ONBOARDING_GATE_ENABLED=false for broad historical tests.
RATE_LIMIT_AI_ASSISTANT_TURN_USER=10000/h for full CI suite determinism.
```

Production must keep the protective defaults.

For a whole-project local boundary, the authoritative command is:

```bash
scripts/ci_django_checks.sh
```

Do not classify redirects from a raw `python manage.py test` invocation as CI regressions until the repository's explicit test environment has been applied. The script preserves production defaults in production while making the historical suite deterministic.

### 4. Avoid invisible dependencies on test order

A test should not pass only when another test ran first. Shared state through cache,
rate limits, global settings or singleton services must be reset or overridden.

### 5. Prefer factories and helpers for common setup

Repeated manual setup increases fragility. Common test data should move toward
helpers/factories, especially for:

```text
users
profiles
wallets
plans
AI proposals
foods/meals/daily plans
```

## Patch checklist

Every functional patch should either add/update an appropriate test or explicitly
state why no test is needed, such as docs-only, CSS-only or copy-only changes.

Before pushing a patch to `staging`:

```text
[ ] Does this patch change a product contract?
[ ] Were related tests updated in the same patch?
[ ] If no test was added, is the reason explicit in the patch notes?
[ ] Are new tests protecting domain behavior rather than copy or implementation detail?
[ ] Are CI/test-only settings explicit?
[ ] Did local focused tests pass?
[ ] Did GitHub Actions pass after push?
```

## Pull request checklist

Before opening or reopening a PR to `main`:

```text
[ ] staging is green in GitHub Actions.
[ ] staging has been manually checked in the web environment when UI/auth flows changed.
[ ] docs/00_current or docs/20_decisions were updated when the patch changed a stable contract.
[ ] no `.orig`, `.rej`, generated files or local artifacts are committed.
```

## Principle

```text
Tests are a living quality contract.
They must help My Scoope evolve safely, not force the product to preserve obsolete
behavior.
```
