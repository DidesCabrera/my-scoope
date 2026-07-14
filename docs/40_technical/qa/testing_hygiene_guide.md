# Testing Hygiene Guide

Status: active
Date: 2026-07-08
Applies to: Django tests, GitHub Actions, staging branch, corrective patches

## Purpose

Tests in My Scoope must accelerate product work by protecting the contracts that
matter. A useful test prevents regressions, documents an accepted behavior, or
makes a risky change safer to ship.

A test is not useful when it only freezes obsolete behavior, depends on execution
order, or fails because of decorative implementation details that are not product
contracts.

## Operating principle

```text
A test should help My Scoope move faster with confidence, not slow the product down with noise.
```

## Test layers

### 1. Domain tests

Domain tests protect business rules and deterministic calculations.

Use them for:

- plan limits and credit/usage accounting;
- nutrition calculations and solver contracts;
- proposal validation/application rules;
- ownership and permission invariants;
- food, meal, daily plan and program calculations.

Expected qualities:

- fast;
- low fixture overhead;
- focused on one rule;
- independent of HTML, URLs and browser behavior.

### 2. Integration tests

Integration tests protect flows that cross app boundaries.

Use them for:

- AI Assistant creating a reviewable proposal;
- proposal approval and application creating owned nutrition entities;
- credits being charged and usage being observable;
- Admin Operations mutating state through audited commands;
- onboarding/profile data feeding solver or proposal context.

Expected qualities:

- fewer than domain tests;
- written around product flows, not private helper internals;
- explicit about settings or feature flags that affect determinism.

### 3. View, URL and template smoke tests

View tests protect that the application can boot, route and render meaningful
screens.

Use them for:

- root URLConf import and resolver health;
- authenticated/anonymous access behavior;
- key pages returning the expected status code;
- template contracts that represent product affordances.

Avoid asserting decorative CSS classes unless the class is itself a stable UI
contract used by JavaScript, QA or documentation.

### 4. Regression tests

Regression tests protect bugs that already happened.

Add one when:

- a bug reached staging;
- a GitHub Actions failure required a corrective patch;
- a local environment issue revealed an unprotected setup contract;
- an auth, limits, proposal, credits or deployment path regressed.

A regression test should make the past failure impossible to miss again. It can be
small; the important part is that its name explains the bug it protects.

### 5. Documentation tests

Documentation tests protect the source of truth.

They should prefer:

```text
docs/00_current/
docs/20_decisions/
```

Only reference `docs/90_archive/` when the test explicitly validates historical
migration context.

## Patch-level rule

Every functional patch should answer one question:

```text
What confidence does this patch add or preserve?
```

Use this matrix:

| Patch type | Expected test response |
| --- | --- |
| Changes business rule | Add/update domain test |
| Changes flow across apps | Add/update integration test |
| Changes route/auth/settings | Add/update view, URL or configuration test |
| Fixes a real bug | Add regression test |
| Changes only docs/CSS/copy | Test may be unnecessary; state why in the patch notes |

## Classifying failures

When a test fails, classify it before changing code.

```text
1. product regression
2. obsolete expectation
3. fragile assertion
4. configuration mismatch
5. fixture/setup issue
```

Do not weaken product code to satisfy an obsolete expectation. Update the test to
the current accepted contract and, when needed, update documentation in the same
patch.

## Naming conventions

Prefer test names that describe the contract:

```python
def test_root_urlconf_imports_with_rate_limited_auth_views():
    ...


def test_approved_proposal_cannot_be_applied_twice():
    ...
```

Avoid generic names:

```python
def test_login():
    ...


def test_flow():
    ...
```

## Local commands

Focused validation during patch work:

```bash
python manage.py check
python manage.py test core.tests.regressions
python manage.py test accounts.tests.test_account_credit_models
```

Regression-only smoke check:

```bash
./scripts/test_regressions.sh
```

Full local suite when preparing a larger PR:

```bash
python manage.py check
python manage.py test
```

CI/staging validation:

```bash
./scripts/ci_django_checks.sh
```

## Environment hygiene

If local behavior differs from GitHub Actions, check dependencies first:

```bash
source venv/bin/activate
pip install -r requirements.txt
python manage.py check
```

A missing package in local development should normally be solved by installing the
project requirements, not by weakening production imports.

## Good test design

Prefer:

- one reason to fail per test;
- stable product contracts over implementation details;
- factories/helpers when setup repeats;
- explicit settings overrides for deterministic CI;
- regression tests for real staging or CI failures.

Avoid:

- test-order dependencies;
- sleeps/time assumptions when a setting override works;
- assertions on decorative copy or CSS;
- broad end-to-end tests when a domain test protects the same contract;
- silent fallbacks that hide missing dependencies.

## Preventive backlog

Recommended next improvements:

```text
1. Create shared factories/helpers for users, profiles, wallets and nutrition entities.
2. Keep `core/tests/regressions/` as the small regression namespace for boot/auth/configuration failures.
3. Add stable data attributes only for UI affordances that need durable tests.
4. Split fast focused checks from full CI only if execution time becomes a bottleneck.
5. Keep docs/00_current and docs/20_decisions aligned with accepted test contracts.
```
