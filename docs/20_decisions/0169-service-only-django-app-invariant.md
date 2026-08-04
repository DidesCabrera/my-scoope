# 0169 · Service-only Django app invariant

Status: accepted
Date: 2026-08-03

## Context

`core` and `nutrition_solver` are installed Django apps but do not own persisted
business entities. Their empty migration packages were previously only an
implicit convention.

## Decision

`core` and `nutrition_solver` remain service-only apps:

```text
core
  -> environment contracts, diagnostics, observability and cross-cutting control

nutrition_solver
  -> pure contracts, deterministic calculation and optimization services
```

Neither app may declare a concrete `models.Model` or add a schema migration. A
future persistence need must first assign ownership to an existing data-owning
domain or record a decision that explicitly changes this invariant.

## Enforcement

`core.tests.regressions.test_service_app_invariants` checks both model modules and
migration directories. This turns the absence of migrations into an executable
architecture contract instead of an undocumented accident.
