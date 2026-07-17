# Decision 0149: close Nutrition Solver Optimization V2 behind activation gates

## Status

Accepted in NSO10; merge remains conditional on green CI and no hard regression.

## Decision

`cp_sat_v1` is available for controlled DailyPlan proposal generation through the `notas` adapter.
The default `heuristic_v2` setting preserves the legacy visible generator and can run CP-SAT in
shadow. Both paths consume the same operational Food boundary; only active, visible,
solver-enabled snapshots are candidates for Optimization V2.

Solver metadata and quality are stored with the pending-review proposal. An impossible active model
stops generation with a structured reason. It does not silently fall back, relax hard constraints,
write a final plan or read Food Catalog directly.

## Consequences

- Rollout and rollback are configuration changes.
- Food Catalog quality is measurably coupled to solver functional quality through versioned snapshots.
- The current heuristic remains available while CP-SAT evidence accumulates.
- NSO00-NSO10 may merge only after focal/global validation and green PR CI.
