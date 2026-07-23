# Decision 0146: CP-SAT is an optional deterministic solver backend

## Status

Accepted in NSO07.

## Decision

Optimization Problem V2 can be solved by `cp_sat_v1` or by the compatible `heuristic_v2` backend.
CP-SAT models selection and portion steps as integer variables, enforces portion bounds, meal
grammar, nutritional ranges and explicit hard food constraints, and minimizes deviation plus small
preference and complexity costs.

The model runs with one worker, a fixed seed and a bounded time limit. Infeasibility is returned as
a structured `impossible` result; hard constraints are never automatically downgraded.

## Consequences

- The backend can compare food selection and portions in one model.
- Results include backend identity, solver status, per-meal portions and daily totals.
- OR-Tools is pinned as an application dependency.
- The heuristic remains available for rollback and shadow comparison.
