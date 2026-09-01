# 0190 - Mobile API domain decomposition closure

Status: completed
Date: 2026-08-31

## Context

Decision 0189 established Comparisons as the safe vertical extraction pattern for
the consumer API. The remaining product routes, schemas and tests still depended
on large compatibility facades, which made ownership and future maintenance harder
to understand even though behavior was covered.

## Decision

MADD00-MADD07 is complete at the repository boundary. The durable contract is:

1. `mobile_api/api.py` owns API construction, shared errors, health and router mounts;
2. product transport lives in domain routers with explicit historical operation IDs;
3. product schemas live in `schema_domains/`, while `schemas.py` provides compatibility
   re-exports plus the platform Error and Health contracts;
4. endpoint behavior lives in focused domain suites, while `test_api_v1.py` verifies
   only the public platform and OpenAPI inventory;
5. application services remain the business-rule authorities;
6. `selectors.py` remains the shared read-model boundary under an exact no-growth budget.

## Evidence

- The generated OpenAPI contract remains current without intentional changes.
- 96 fast tests and all 48 Mobile API tests passed.
- The complete 1,812-test Django suite passed in 292.325 seconds.
- Branch coverage is 78% against the enforced 75% minimum.
- Ruff, complexity, mypy, dependency audit, migrations, repository hygiene and
  document registry checks passed.
- `api.py` decreased from 1,544 to 69 lines, `schemas.py` from 1,249 to 207 and
  `test_api_v1.py` from 2,055 to 87.

## Consequences

- A maintainer can find transport, schemas and behavioral evidence by domain name.
- Architecture tests prevent product routes or schemas from returning to the facades.
- Compatibility imports protect callers while new code can import domain contracts directly.
- Selector decomposition is deferred until ownership can improve without duplicating
  cross-domain projections.
- PostgreSQL CI and physical iOS/staging behavior remain external validation gates.
