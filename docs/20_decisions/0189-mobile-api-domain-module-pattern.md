# 0189 - Mobile API domain module pattern

Status: accepted
Date: 2026-08-31

## Context

CQC made route ownership and facade growth executable, but finding one mobile
feature still required navigating the large `api.py`, `schemas.py` and
`test_api_v1.py` compatibility files. A big-bang rewrite would create unnecessary
OpenAPI, authorization and test-discovery risk.

## Decision

Mobile API decomposition proceeds one cohesive domain at a time using Comparisons
as the reference pattern:

- `api.py` owns API construction, shared exception handlers and router mounting;
- `routes/<domain>.py` owns transport, auth/scopes and explicitly pinned historical
  operation IDs;
- `schema_domains/<domain>.py` owns independent request/response schemas;
- existing application services remain product-rule authorities;
- `tests/test_<domain>_api.py` owns endpoint behavior and reuses the authenticated base;
- `schemas.py` and remaining facades re-export compatibility names during migration.

Moved routes must produce byte-identical committed OpenAPI unless a separate product
decision changes the interface. Router tags or automatic module-derived operation IDs
must not leak into the contract as accidental refactor effects.

## Consequences

- A maintainer can follow one domain vertically without reading the whole transport facade.
- Each extraction is independently reviewable and reversible.
- Compatibility facades remain temporarily, but their exact budgets must decrease.
- Some route modules may retain imports from legacy selectors until their domain projection is extracted later.

## Implemented result

The completed decomposition leaves `api.py` as the API construction/error/health
composition root and `schemas.py` as a compatibility re-export surface plus the
platform Error and Health contracts. Eight domain routers and seven schema-domain
modules own the product interfaces. `selectors.py` remains deliberately shared as
the read-model boundary used across calendarization and library projections.
