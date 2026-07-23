# 0139 - Nutrition Solver Optimization V2 baseline

Status: accepted
Date: 2026-07-16
Cycle: NSO00

## Decision

Open NSO00-NSO10 as one integrated evolution spanning Food Catalog capability data, the
operational snapshot boundary in `notas`, and deterministic optimization in `nutrition_solver`.

The apps collaborate through versioned pure contracts. Collaboration does not permit the solver
to read the master catalog directly. The accepted path remains:

```text
CatalogFood -> explicit published snapshot -> notas.Food -> pure solver projection
```

Quality will be measured against frozen golden scenarios rather than only by a lower opaque
score. Hard constraints, deterministic execution, proposal review and rollback remain release
gates.

## Consequences

- The v2 coordinate solver becomes the named compatibility baseline `heuristic_v2`.
- New feature data must declare provenance, confidence and missing-value behavior.
- Food classification can become multi-capability rather than one exclusive category.
- Selection and portions may be optimized jointly by a later backend.
- Activation occurs only after shadow comparison and global CI.
