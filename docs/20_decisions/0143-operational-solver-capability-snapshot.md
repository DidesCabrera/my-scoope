# 0143 - Operational Solver capability snapshot

Status: accepted
Date: 2026-07-16
Cycle: NSO04

## Decision

Solver capabilities cross the Food Catalog boundary only inside the explicit publication
snapshot. `notas.Food` stores a versioned operational capability payload; the adapter creates a
pure `SolverFoodProfile` without exposing master IDs or reading `CatalogFood` at solve time.

If curated functional roles are absent, the adapter may add an explicitly derived and versioned
macro-role feature. It never writes the derived value back to the master implicitly.
